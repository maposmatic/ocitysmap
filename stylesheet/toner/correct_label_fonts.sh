#!/bin/sh

sed -i 's/Italic/Oblique/' labels.mss
sed -i 's/Arial Unicode MS Regular/DejaVu Sans/' labels.mss
sed -i 's/Arial Regular/DejaVu Sans/' labels.mss
sed -i 's/Arial Unicode MS/DejaVu Sans/' labels.mss
sed -i 's/Arial Regular/DejaVu/' labels.mss
sed -i 's/Arial Bold/DejaVu Sans Bold/' labels.mss
