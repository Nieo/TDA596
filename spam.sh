
for j in `seq 1 32`; do
	for i in `seq 1 50`; do curl -d 'entry=number'${i}'-vessel'${j} -X 'POST' 'http://10.1.0.'${j}'/board'; done &
done