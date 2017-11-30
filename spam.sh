
for j in `seq 1 10`; do
	for i in `seq 1 2`; do curl -d 'entry=number'${i}'-vessel'${j} -X 'POST' 'http://10.1.0.'${j}'/board'; done &
done