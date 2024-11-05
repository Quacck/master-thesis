This is the repository of my master thesis with the following abstract:

    Due to rising energy demand by datacenters, the need to use energy more carbon-
    efficiently is pressing. This thesis contributes to the field of carbon-aware scheduling, i.e., executing workloads in datacenters based on the current energy mix.
    We conduct a structured literature review to find that prior work uses a simple workload model of constant power that neglects overhead associated with resuming workloads.
    Through power measurements of a machine learning program, we find that the workload
    commonly used to motivate suspend & resuming scheduling, is more complex. We introduce our workload model Stawp which incorporates startup and working phases of
    different power. Our testbed Carbs implements two new scheduling algorithms, for non-suspendible and suspendible workloads, that take account of these differently powered phases and overhead on resumption. Carbs builds upon an existing testbed. We evaluate our new workload model against the old across different workloads and schedulers.
    Our findings are preliminary: We observe that trends under the simple workload model
    apply to Stawp as well. Specifically, longer workloads and longer deadlines, increase the potential for carbon-emission reductions through a suspend & resume strategy - even when accounting for overhead. The effects of power heterogeneity will need more examination in future work. For this, we offer Carbs to the scientific community.

It includes:
 
+ The latex code for building the .pdf (see `/content` and `/`)
+ `/power-measurements` holds all data from the measurements and the Jupyter notebooks for building the figures
+ `/notes` contains preliminary notes I made along working on my thesis. They are an unedited collection of thoughts made for the writing process.
+ `/literature_study` holds a .csv of the reviewed papers
+ `/agorameter` was used for some carbon emission plots used in the thesis
+ `/traces` contains Scorelab traces that I investigated along the way, but that did not make it into the final paper.

Building the thesis from scratch might not work, `thesis_final.pdf` is the submitted version, however. Also be aware to pull submodules, as the main implementation, `carbs`, is one.