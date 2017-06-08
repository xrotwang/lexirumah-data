set -e

python process_data.py
echo "Segmenting…"
python segment.py all_data.tsv tap-segmented.tsv
echo "Generating PMI scores…"
online_pmi --gop -2.5 --gep -1.75 --pmidict pmi-scores --reader cldf tap-segmented.tsv --trans IPA > /dev/null
echo "Autocoding…"
python autocode.py tap-segmented.tsv tap-autocode.tsv --lodict pmi-scores
echo "Merging…"
python merge.py tap-autocode.tsv tap-merged.tsv --log
echo "Aligning…"
python align.py tap-merged.tsv tap-aligned-cldf.tsv --guide ~/devel/CogDetect/tree.tree --only --lodict pmi-scores
echo "Preparing for edictor…"
python lingpycldf.py --cldf-to-lingpy tap-aligned-cldf.tsv tap-aligned.tsv
echo "Comparing with original data…"
python uncognates.py tap-aligned.tsv --print
