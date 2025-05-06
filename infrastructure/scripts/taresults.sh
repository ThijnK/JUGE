#!/bin/bash

# author: Thijn Kroon (2025)

find . -type f \( -name \*\transcript\.csv \) > transcript_files.txt
tar -zcvf transcripts.tar.gz -T transcript_files.txt
rm transcript_files.txt