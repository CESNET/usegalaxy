# Test Results (powered by Planemo)

## Test Summary

<div class="progress">
  <div class="progress-bar progress-bar-success" style="width: 100.0%" aria-valuenow="8" aria-valuemin="0" aria-valuemax="8" data-toggle="tooltip" title="8 Passed">
  </div>
  <div class="progress-bar progress-bar-warning" style="width: 0.0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="8" data-toggle="tooltip" title="0 Skipped">
  </div>
  <div class="progress-bar progress-bar-danger" style="width: 0.0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="8" title="0 Failed or Errored">
  </div>
</div>

| Test State | Count |
| ---------- | ----- |
| Total      | 8 |
| Passed     | 8 |
| Error      | 0 |
| Failure    | 0 |
| Skipped    | 0 |


<details ><summary>Passed Tests</summary>

* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 1)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23760/inputs/dataset_d9013f14-d840-4c92-85d5-5a89d5a60885.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23760/outputs/dataset_258ce544-a18f-4670-8f47-0cd0f78924ce_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23760/outputs/dataset_258ce544-a18f-4670-8f47-0cd0f78924ce_files'   --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23760/outputs/dataset_258ce544-a18f-4670-8f47-0cd0f78924ce_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23760/outputs/dataset_258ce544-a18f-4670-8f47-0cd0f78924ce_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911783.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | limits | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastqsanger" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 2)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/inputs/dataset_eeb4de90-5a0d-4c01-8513-c242ff6e9aa0.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/outputs/dataset_334ef537-5a4b-45f4-8038-774aef05aee0_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/outputs/dataset_334ef537-5a4b-45f4-8038-774aef05aee0_files' --contaminants '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/inputs/dataset_cda10ace-672e-4e18-8bd3-b14e2503dad9.dat'   --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/outputs/dataset_334ef537-5a4b-45f4-8038-774aef05aee0_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23763/outputs/dataset_334ef537-5a4b-45f4-8038-774aef05aee0_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911792.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | adapters | ` None ` |
       | limits | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastqsanger" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 3)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/inputs/dataset_6c254618-871e-4904-b3a6-e83816cef17a.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/outputs/dataset_47b245f7-a23c-4f71-bb10-cdf6af5b27a3_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/outputs/dataset_47b245f7-a23c-4f71-bb10-cdf6af5b27a3_files'  --adapters '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/inputs/dataset_459aa368-af33-4cbd-993f-10bc0d225f80.dat'  --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/outputs/dataset_47b245f7-a23c-4f71-bb10-cdf6af5b27a3_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23766/outputs/dataset_47b245f7-a23c-4f71-bb10-cdf6af5b27a3_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911804.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | limits | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastqsanger" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 4)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/inputs/dataset_0827f3d7-afcb-473e-8604-a40e5b395d39.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/outputs/dataset_c3793f33-e56c-42d4-890e-ff9c218c851e_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/outputs/dataset_c3793f33-e56c-42d4-890e-ff9c218c851e_files'   --limits '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/inputs/dataset_60267dcb-23c5-4e5d-b00e-0ef5f433fa83.dat' --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/outputs/dataset_c3793f33-e56c-42d4-890e-ff9c218c851e_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23769/outputs/dataset_c3793f33-e56c-42d4-890e-ff9c218c851e_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911805.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastqsanger" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 5)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/inputs/dataset_7796baac-5195-4111-bcfd-0e48e56b7b4f.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/outputs/dataset_12a8ea77-85c2-4a8f-8c06-4207b8a2b949_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/outputs/dataset_12a8ea77-85c2-4a8f-8c06-4207b8a2b949_files'   --limits '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/inputs/dataset_4ed436cc-ff83-4172-b7dc-646af0591cf0.dat' --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 3 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/outputs/dataset_12a8ea77-85c2-4a8f-8c06-4207b8a2b949_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23772/outputs/dataset_12a8ea77-85c2-4a8f-8c06-4207b8a2b949_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911813.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "3" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastq" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 6)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23774/inputs/dataset_4cd006ff-7431-4052-a131-071ccf146e24.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23774/outputs/dataset_ea7932c9-dd02-4ec7-bd95-02098d9c7bd1_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23774/outputs/dataset_ea7932c9-dd02-4ec7-bd95-02098d9c7bd1_files'   --threads ${GALAXY_SLOTS:-2} --quiet --extract --min_length 108  --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23774/outputs/dataset_ea7932c9-dd02-4ec7-bd95-02098d9c7bd1_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23774/outputs/dataset_ea7932c9-dd02-4ec7-bd95-02098d9c7bd1_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911816.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | limits | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "108" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastqsanger" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 7)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23776/inputs/dataset_21f185aa-0129-4dbe-b18b-318aed9d3c5d.dat' '1000trimmed_fastq' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23776/outputs/dataset_94c5642c-de1d-45b1-b2a3-34fcf22da0ee_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23776/outputs/dataset_94c5642c-de1d-45b1-b2a3-34fcf22da0ee_files'   --threads ${GALAXY_SLOTS:-2} --quiet --extract --nogroup --kmers 7 -f 'fastq' '1000trimmed_fastq'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23776/outputs/dataset_94c5642c-de1d-45b1-b2a3-34fcf22da0ee_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23776/outputs/dataset_94c5642c-de1d-45b1-b2a3-34fcf22da0ee_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911818.pbs-m1.metacentrum.cz

      ```
    **Standard Output:**

    * ```console
      null

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | limits | ` None ` |
       | nogroup | ` true ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "fastq" ` |



    </div></details>


* <details class="rcorners light-green"><summary class="light-green">&#9989; toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc (Test # 8)</summary><div class="padded">

    **Command Line:**

    * ```console
      ln -s '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23778/inputs/dataset_e9589f46-e33d-4bdb-a26c-ae5aaaf55ad7.dat' 'hisat_output_1_bam' && mkdir -p '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23778/outputs/dataset_9188f380-8f5e-4c9f-9d86-cd5ee687ee89_files' && fastqc --outdir '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23778/outputs/dataset_9188f380-8f5e-4c9f-9d86-cd5ee687ee89_files'   --threads ${GALAXY_SLOTS:-2} --quiet --extract  --kmers 7 -f 'bam' 'hisat_output_1_bam'  && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23778/outputs/dataset_9188f380-8f5e-4c9f-9d86-cd5ee687ee89_files'/*/fastqc_data.txt output.txt && cp '/auto/praha5-elixir/home/galaxyeu/pulsar-cz/files/staging/23778/outputs/dataset_9188f380-8f5e-4c9f-9d86-cd5ee687ee89_files'/*\.html output.html
      ```
    **Exit Code:**

    * ```console
      0
      ```
    **Standard Error:**

    * ```console
      Picked up JAVA_TOOL_OPTIONS: -Xmx32g -Djava.io.tmpdir=/scratch/galaxyeu/job_7911819.pbs-m1.metacentrum.cz

      ```
   **Job Parameters:**

   *   | Job parameter | Parameter value |
       | ------------- | --------------- |
       | contaminants | ` None ` |
       | adapters | ` None ` |
       | limits | ` None ` |
       | nogroup | ` false ` |
       | min\_length | ` "" ` |
       | kmers | ` "7" ` |
       | chromInfo | ` "/rbd/data/tool_data/shared/ucsc/chrom/?.len" ` |
       | dbkey | ` "?" ` |
       | \_\_input\_ext | ` "bam" ` |



    </div></details>


</details>
