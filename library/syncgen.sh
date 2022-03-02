GENOR=`find $1 -name genutils.py`
for gen in `find /home/chidi/repos/XNAT -name genutils.py`
do
echo "-------------------------------------------"
echo "Comparing $GENOR to $gen"
diff $GENOR $gen
echo "--------------------------------------------"
done
