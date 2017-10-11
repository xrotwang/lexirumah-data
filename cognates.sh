rm ../lexibank/lexibank.sqlite

# Break on error
set -e
python3 pylexirumah/process_data.py
echo "Segmenting…"
python3 pylexirumah/segment.py all_data.tsv tap-segmented.tsv
echo "Generating PMI scores…"
online_pmi --gop -2.5 --gep -1.75 --pmidict pmi-scores --reader cldf tap-segmented.tsv --trans IPA > /dev/null
echo "Autocoding…"
python3 pylexirumah/autocode.py tap-segmented.tsv tap-autocode.tsv --lodict pmi-scores
echo "Merging…"
python3 pylexirumah/merge.py tap-autocode.tsv tap-merged.tsv --log
echo "Aligning…"
python3 pylexirumah/align.py tap-merged.tsv tap-aligned-cldf.tsv --guide ~/devel/CogDetect/tree.tree --only --lodict pmi-scores
echo "Preparing for edictor…"
python3 pylexirumah/lingpycldf.py --cldf-to-lingpy tap-aligned-cldf.tsv tap-aligned.tsv
echo "Comparing with original data…"
python3 pylexirumah/uncognates.py tap-aligned.tsv --print
