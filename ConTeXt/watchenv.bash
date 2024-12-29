#!/bin/bash
inotifywait -r -m -e modify $1 | 
   while read file_path file_event file_name; do 
       echo ${file_path}${file_name} event: ${file_event}
       context --environment=${file_path}${file_name} $2
   done
# context --environment=phase1and2_convert.tex ../edited/CME_phase_1-2/Merlin.xml
