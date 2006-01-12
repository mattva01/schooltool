#!/bin/sh
# Generate png files out of GraphViz .dot source files.
# You need to have graphviz and ImageMagic installed
for n in 1 2 3 4 5 6; do
  dot -Tpng -o ttschema-wizard-$n.png ttschema-wizard-$n.dot
  mogrify -resize 50% ttschema-wizard-$n.png
  convert -resize 25% ttschema-wizard-$n.png ttschema-wizard-$n-tiny.png
done
