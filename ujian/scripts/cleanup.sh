curl -X POST -H "Content-Type: application/json" localhost:5000/teacher/tokens/cleanup -d '{"force":"true"}'
curl -X POST -H "Content-Type: application/json" localhost:5000/teacher/sessions/cleanup -d '{"force":"true"}'
