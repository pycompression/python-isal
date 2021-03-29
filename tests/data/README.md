Data was generated using [dwgsim](
https://github.com/nh13/dwgsim) version 0.1.11.

The reference genome used to generate the data was [the GRCh38 assembly 
including alt contigs and decoy sequences provided by NCBI](
ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_full_plus_hs38d1_analysis_set.fna.gz).

The commands used to generate the data were:

```
dwgsim -N 10000 -e 0.0010 -E 0.0010 -1 152 -2 152 -c 0 -S1 -z 1 -Q 5 \
reference.fasta test
gzip -c -9 test.bwa.read1.fastq > test.fastq.gz
```

concatenated.fastq.gz was created with:
```
gzip -cd tests/data/test.fastq.gz | head -n 1000 | gzip -c -1 >> test2.fastq.gz
gzip -cd tests/data/test.fastq.gz | head -n 1000 | gzip -c -1 >> test2.fastq.gz
```
