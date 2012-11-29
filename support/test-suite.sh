#!/bin/bash

# Basic test suite for OcitySMap.

# type:title:area:renderer:paper_format:paper_orientation
#
#  where type is either osmid or bbox
TESTS=(
    "osmid:Fignévelle:-933177:plain:A3:portrait"
    "osmid:Fignévelle:-933177:plain:A2:landscape"
    "osmid:Godoncourt:-933173:single_page_index_side:A1:landscape"
    "osmid:Godoncourt:-933173:single_page_index_bottom:A1:portrait"
    "osmid:Issy-les-Moulineaux:-85527:multi_page:A5:portrait"
    "osmid:Issy-les-Moulineaux:-85527:multi_page:A4:landscape"
    "osmid:LeQuiou:-381059:plain:A1:portrait"
    "bbox:ColomiersLycée:43.6260,1.2972-43.6163,1.3144:single_page_index_side:A4:portrait"
    "bbox:ColomiersLycée:43.6260,1.2972-43.6163,1.3144:single_page_index_bottom:A4:landscape"
    "bbox:AutourDeLyon:45.7850,4.7795-45.7277,4.9038:multi_page:A4:portrait"
)

TESTID=0

for tst in ${TESTS[@]} ; do
  type=$(echo $tst | cut -f1 -d':')
  title=$(echo $tst | cut -f2 -d':')
  ref=$(echo $tst | cut -f3 -d':')
  renderer=$(echo $tst | cut -f4 -d':')
  paper_format=$(echo $tst | cut -f5 -d':')
  paper_orientation=$(echo $tst | cut -f6 -d':')

  if [ $type == "osmid" ] ; then
    area_opt="--osmid=$ref"
  else
    bbox_part1=$(echo $ref|cut -f1 -d'-')
    bbox_part2=$(echo $ref|cut -f2 -d'-')
    area_opt="-b ${bbox_part1} ${bbox_part2}"
  fi

  if [ $renderer == "multi_page" ] ; then
    output_formats="-f pdf"
  else
    output_formats="-f png -f pdf -f svgz"
  fi

  printf "\e[31m>>> Starting test with\n area='%s'\n renderer='%s'\n formats='%s'\n paper='%s'\n orientation='%s'\n title='%s'\n\n\e[m" \
    "$area_opt" \
    "$renderer" \
    "$output_formats" \
    "$paper_format" \
    "$paper_orientation" \
    "$title"

  ./render.py \
    $output_formats \
    -l $renderer \
    $area_opt \
    -p test_$TESTID \
    -t "$title" \
    --paper-format=$paper_format \
    --orientation=$paper_orientation

  if [ $? -ne 0 ] ; then
    echo "==== ERROR, ABORTING"
    exit 1
  fi
  TESTID=$((TESTID+1))
done
