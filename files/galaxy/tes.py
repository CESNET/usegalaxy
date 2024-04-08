"""
Job control via TES.
"""
import logging
import os
import shlex

import pulsar
import requests

from galaxy import model
from galaxy.jobs import JobWrapper
from galaxy.jobs.command_factory import build_command
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.util import asbool

log = logging.getLogger(__name__)

__all__ = ('TESJobRunner', )

GENERIC_REMOTE_ERROR = "Failed to communicate with remote job server"
FAILED_REMOTE_ERROR = "Remote job server indicated a problem running or monitoring the job."
LOST_REMOTE_ERROR = "Remote job server could not determine the job's state."

DEFAULT_GALAXY_URL = "http://localhost:8080/"


class TESJobState(AsynchronousJobState):
    def __init__(self, **kwargs):
        """
        Encapsulates state related to a job.
        """
        super().__init__(**kwargs)
        self.user_log = None
        self.user_log_size = 0
        self.cleanup_file_attributes = ['output_file', 'error_file', 'exit_code_file']


class TESJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "TESJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """
            Initialize this job runner and start the monitor thread
        """
        super().__init__(app, nworkers, **kwargs)
        self.container_workdir = "/tmp"
        if (hasattr(app.config, "galaxy_infrastructure_url")):
            self.galaxy_url = f"{app.config.galaxy_infrastructure_url.rstrip('/')}/"
        else:
            raise Exception("Galaxy URL isn't specified")

        self.running_states = ["RUNNING", "INITIALIZING", "QUEUED", "PAUSED"]
        self.complete_states = ["COMPLETE"]
        self.error_states = ["EXECUTOR_ERROR", "SYSTEM_ERROR", "CANCELED", "UNKNOWN"]
        self.cancel_state = ["CANCELED"]

        self._init_monitor_thread()
        self._init_worker_threads()

    def _send_task(self, master_addr: str, task: dict):
        """
            Send job-script to TES
        """
        log.debug("Sending job script to TES Server")
        url = f"{master_addr}/v1/tasks"
        try:
            req = requests.post(url, json=task)
            try:
                job_id = req.json()["id"]
                return job_id
            except KeyError:
                log.error(f"TES Server failed to accept the job {req.json()}")
        except requests.exceptions.RequestException:
            log.error(f"{GENERIC_REMOTE_ERROR} on URL {master_addr}")

    def _get_job(self, master_addr: str, job_id: str, view: str = "MINIMAL"):
        """
            Get Job Status from TES Server
        """
        log.debug(f"Getting status for job id {job_id}")
        url = f"{master_addr}/v1/tasks/{str(job_id)}"
        try:
            req = requests.get(url, params={'view': view})
            return req.json()
        except requests.exceptions.RequestException:
            log.error(f"{LOST_REMOTE_ERROR} for job id {job_id}")

    def _cancel_job(self, master_addr: str, job_id: str):
        """
            Cancel the Job on TES Server
        """
        log.debug(f"Cancelling the job id {job_id}")
        url = f"{master_addr}/v1/tasks/{job_id}:cancel"
        try:
            requests.post(url)
        except requests.exceptions.RequestException:
            log.error(f"{GENERIC_REMOTE_ERROR} for cancellation of job id {job_id}")

    def get_upload_path(self, job_id: str, env=None):
        """
            For getting upload URL for staging in the files
        """
        if env is None:
            env = []

        encoded_job_id = self.app.security.encode_id(job_id)
        job_key = self.app.security.encode_id(job_id, kind="jobs_files")
        endpoint_base = "%sapi/jobs/%s/files?job_key=%s"

        if self.app.config.nginx_upload_job_files_path:
            endpoint_base = "%s" + \
                            self.app.config.nginx_upload_job_files_path + \
                            "?job_id=%s&job_key=%s"

        files_endpoint = endpoint_base % (
            self.galaxy_url,
            encoded_job_id,
            job_key
        )

        get_client_kwds = dict(
            job_id=str(job_id),
            files_endpoint=files_endpoint,
            env=env
        )
        return get_client_kwds

    def file_creation_executor(self, docker_image: str, work_dir: str):
        """
        Returns the executor for creation of files
        """
        file_executor = {
            "workdir": "/",
            "image": docker_image,
            "command": ["/bin/bash", os.path.join(work_dir, 'createfiles.sh')]
        }
        return file_executor

    def job_executor(self, remote_image: str, command_line: str, env: dict, work_dir: str):
        """
        Returns the executor for executing jobs
        """
        command_list = shlex.split(command_line)
        replacements = {'../outputs/tool_stdout': 'tool_stdout',
                        '../outputs/tool_stderr;': 'tool_stderr;'}
        command_list = [replacements.get(item, item) for item in command_list]
        job_executor = {
            "workdir": work_dir,
            "image": remote_image,
            "command": command_list,
            "env": env
        }
        return job_executor

    def file_staging_out_executor(self, docker_image: str, command: list):
        """
        Returns the executor for staging out of the files
        """
        staging_out_executor = {
            "workdir": "/",
            "image": docker_image,
            "command": command
        }
        return staging_out_executor

    def base_job_script(self, mounted_dir: list, work_dir: str, description: str):
        """
        Retruns the basic structure for job-script
        """
        execution_script = {
            "name": "Galaxy Job Execution",
            "description": description,
            "inputs": [],
            "outputs": [],
            "executors": [],
            "volumes": mounted_dir
        }

        return execution_script

    def output_file_gen_script(self, output_files: list):
        """
            Generates shell script for generating output files in container
        """
        script = []

        for file in output_files:
            dir_name = os.path.split(file)[0]
            script.extend(['mkdir', '-p', dir_name, '&&', 'touch', file, '&&'])

        script[-1] = '\n'
        return ' '.join(script)

    def env_variables(self, job_wrapper: JobWrapper):
        """
            Get environment variables from job_wrapper
        """
        env_vars = {}
        for variable in job_wrapper.environment_variables:
            env_vars[variable['name']] = variable['value']

        for variable in job_wrapper.job_destination.env:
            env_vars[variable['name']] = variable['value']

        env_vars["_GALAXY_JOB_TMP_DIR"] = self.container_workdir
        env_vars["_GALAXY_JOB_HOME_DIR"] = self.container_workdir
        return env_vars

    def inout_url(self, api_url: str, path: str):
        """
            Get URL for path
        """
        file_link = f"{api_url}&path={path}"
        return file_link

    def in_descriptors(self, api_url: str, in_paths: list, type: str = "FILE"):
        """
            Get Input / Output Descriptor for Jobfile
        """
        in_description = []

        for path in in_paths:
            in_description.append({
                "url": self.inout_url(api_url, path),
                "path": path,
                "type": type
            })
        return in_description

    def out_descriptors(self, api_url: str, out_paths: list[dict], type: str = "FILE"):
        """
            Get Input / Output Descriptor for Jobfile
        """
        out_description = []

        for path in out_paths:
            out_description.append({
                "url": self.inout_url(api_url, path['return_path']),
                "path": path['tes_path'],
                "type": type
            })
        return out_description


    def get_job_directory_files(self, work_dir: str):
        """
        Get path for all the files from work directory
        """
        paths = []
        for root, _, files in os.walk(work_dir):
            for file in files:
                paths.append(os.path.join(root, file))

        return paths

    def get_docker_image(self, job_wrapper: JobWrapper):
        """
            For getting the docker image to be used
        """
        remote_container = self._find_container(job_wrapper)
        remote_image = None
        staging_docker_image = None

        if (hasattr(job_wrapper.job_destination, "params")):
            if ("default_docker_image" in job_wrapper.job_destination.params):
                remote_image = job_wrapper.job_destination.params.get("default_docker_image")

        if (hasattr(job_wrapper.job_destination, "params")):
            if ("staging_docker_image" in job_wrapper.job_destination.params):
                staging_docker_image = job_wrapper.job_destination.params.get("staging_docker_image")

            else:
                staging_docker_image = remote_image

        if (hasattr(remote_container, "container_id")):
            remote_image = remote_container.container_id

        if (staging_docker_image is None):
            staging_docker_image = remote_image

        if (remote_image is None):
            raise Exception("default_docker_image not specified")
        else:
            return remote_image, staging_docker_image

    def build_script(self, job_wrapper: JobWrapper, client_args: dict):
        """
        Returns the Job script with required configurations of the job
        """
        tool_dir = job_wrapper.tool.tool_dir
        work_dir = job_wrapper.working_directory
#        object_store_path = job_wrapper.object_store.file_path		# DEMON change

        input_files = self.__get_inputs(job_wrapper)
        output_files_dict = self.get_output_files(job_wrapper)
        extra_files = job_wrapper.extra_filenames
        tool_files = pulsar.client.staging.up.JobInputs(job_wrapper.command_line, extra_files).find_referenced_subfiles(tool_dir)

        remote_image, staging_out_image = self.get_docker_image(job_wrapper)

        command_line = build_command(
            self,
            job_wrapper=job_wrapper,
            include_metadata=False,
            create_tool_working_directory=False,
            include_work_dir_outputs=False,
            remote_job_directory=work_dir
        )

        env_var = self.env_variables(job_wrapper)
        staging_out_url = None
        if (hasattr(job_wrapper.job_destination, "params")):
            if ("stage_out_url" in job_wrapper.job_destination.params):
                encoded_job_id = self.app.security.encode_id(job_wrapper.job_id)
                job_key = self.app.security.encode_id(job_wrapper.job_id, kind="jobs_files")
                endpoint_base = "%sapi/jobs/%s/files?job_key=%s"
                staging_out_url = endpoint_base % (job_wrapper.job_destination.params.get("stage_out_url"), encoded_job_id, job_key)

        if (staging_out_url is None):
            staging_out_url = client_args['files_endpoint']


#        job_script = self.base_job_script([work_dir, object_store_path], work_dir, job_wrapper.tool.description)	# DEMON change
        job_script = self.base_job_script([work_dir], work_dir, job_wrapper.tool.description)

        job_script["inputs"].extend(self.in_descriptors(client_args['files_endpoint'], tool_files))
        job_script["inputs"].extend(self.in_descriptors(client_args['files_endpoint'], self.get_job_directory_files(work_dir)))
        job_script["inputs"].extend(self.in_descriptors(client_args['files_endpoint'], input_files))

        job_script["outputs"].extend(self.out_descriptors(client_args['files_endpoint'], output_files_dict))

        job_script["executors"].append(self.job_executor(remote_image, command_line, env_var, work_dir))

        return job_script

    def __get_inputs(self, job_wrapper: JobWrapper):
        """Returns the list about the details of input files."""

        input_files = []

        for input_dataset_wrapper in job_wrapper.job_io.get_input_paths():
            path = str(input_dataset_wrapper)
            input_files.append(path)

        return input_files

    def queue_job(self, job_wrapper: JobWrapper):
        """Submit the job to TES."""

        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")

        include_metadata = asbool(job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
        if not self.prepare_job(job_wrapper, include_metadata=include_metadata):
            return

        job_id = job_wrapper.job_id
        client_args = self.get_upload_path(job_id)
        job_destination = job_wrapper.job_destination
        galaxy_id_tag = job_wrapper.get_id_tag()
        master_addr = job_destination.params.get("tes_master_addr")

        job_script = self.build_script(job_wrapper, client_args)
        job_id = self._send_task(master_addr, job_script)

        if (job_id is None):
            log.debug(f"Unable to set job on TES instance {master_addr}")
            return

        job_state = TESJobState(
            job_id=job_id,
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper
        )

        log.info("(%s) queued as %s" % (galaxy_id_tag, job_id))
        job_wrapper.set_job_destination(job_destination, job_id)
        self.monitor_job(job_state)

    def get_output_files(self, job_wrapper: JobWrapper):
        """
        Utility for getting list of Output Files
        """
        out_dicts = []
        work_dir = job_wrapper.working_directory
        existing_fpaths = []
        for pair in self.get_work_dir_outputs(job_wrapper):
            out_dicts.append({
                'tes_path': work_dir + "/" + os.path.basename(pair[0]),
                'return_path': pair[1]
            })
            existing_fpaths.append(pair[1])
        for output in job_wrapper.job_io.get_output_fnames():
            if str(output) not in existing_fpaths:
                out_dicts.append({
                    'tes_path': str(output),
                    'return_path': str(output)
                })

        return out_dicts

    def __finish_job(self, data: dict, job_wrapper: JobWrapper):
        """
        Utility for finishing job after completion
        """
        stdout = self._concat_job_log(data, 'stdout')
        stderr = self._concat_job_log(data, 'stderr')
        exit_code = self._get_exit_codes(data)

        job_metrics_directory = os.path.join(job_wrapper.working_directory, "metadata")
        try:
            job_wrapper.finish(
                stdout,
                stderr,
                exit_code,
                job_metrics_directory=job_metrics_directory,
            )
        except Exception:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def _concat_job_log(self, data: dict, key: str):
        """"
        Utility for concatination required job logs
        """
        logs_data = data.get('logs')
        log_lines = []
        for log in (logs_data or []):
            if ('logs' in log):
                for log_output in log.get('logs'):
                    log_line = log_output.get(key)
                    if log_line is not None:
                        log_lines.append(log_line)
        return "\n".join(log_lines)

    def _get_exit_codes(self, data: dict):
        """"
        Utility for getting out exit code of the job
        """
        if (data['state'] == "COMPLETE"):
            return 0
        else:
            return 1

    def check_watched_item(self, job_state: TESJobState):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        job_id = job_state.job_id
        galaxy_id_tag = job_state.job_wrapper.get_id_tag()
        master_addr = job_state.job_wrapper.job_destination.params.get("tes_master_addr")

        data = self._get_job(master_addr, job_id, "FULL")
        state = data['state']

        job_running = state in self.running_states
        job_complete = state in self.complete_states
        job_failed = state in self.error_states
        job_cancel = state in self.cancel_state

        if job_running and job_state.running:
            return job_state

        if job_running and not job_state.running:
            log.debug("(%s/%s) job is now running" % (galaxy_id_tag, job_id))
            job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            job_state.running = True
            return job_state

        if not job_running and job_state.running:
            log.debug("(%s/%s) job has stopped running" % (galaxy_id_tag, job_id))
            if (job_cancel):
                job_state.job_wrapper.change_state(model.Job.states.DELETED)
                job_state.running = False
                self.__finish_job(data, job_state.job_wrapper)
                return

        if job_complete:
            if job_state.job_wrapper.get_state() != model.Job.states.DELETED:
                external_metadata = asbool(job_state.job_wrapper.job_destination.params.get("embed_metadata_in_job", True))
                if external_metadata:
                    self._handle_metadata_externally(job_state.job_wrapper, resolve_requirements=True)

                self.__finish_job(data, job_state.job_wrapper)
                log.debug("(%s/%s) job has completed" % (galaxy_id_tag, job_id))
            return

        if job_failed:
            log.debug("(%s/%s) job failed" % (galaxy_id_tag, job_id))
            self.__finish_job(data, job_state.job_wrapper)
            return

        return job_state

    def stop_job(self, job_wrapper: JobWrapper):
        """Attempts to delete a task from the task queue"""
        job = job_wrapper.get_job()

        job_id = job.job_runner_external_id
        if job_id is None:
            return

        master_addr = job.destination_params.get('tes_master_addr')
        self._cancel_job(master_addr, job_id)

    def recover(self, job: model.Job, job_wrapper: JobWrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put(job_wrapper)
            return
        job_state = TESJobState(job_wrapper=job_wrapper, files_dir=self.app.config.job_working_directory)
        job_state.job_id = str(job_id)
        job_state.job_wrapper = job_wrapper
        job_state.job_destination = job_wrapper.job_destination
        job_state.user_log = os.path.join(self.app.config.job_working_directory, 'galaxy_%s.tes.log' % galaxy_id_tag)
        job_state.register_cleanup_file_attribute('user_log')
        if job.state == model.Job.states.RUNNING:
            log.debug("(%s/%s) is still in running state, adding to the DRM queue" % (job.id, job.job_runner_external_id))
            job_state.running = True
            self.monitor_queue.put(job_state)
        elif job.state == model.Job.states.QUEUED:
            log.debug("(%s/%s) is still in DRM queued state, adding to the DRM queue" % (job.id, job.job_runner_external_id))
            job_state.running = False
            self.monitor_queue.put(job_state)
