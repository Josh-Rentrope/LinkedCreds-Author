#!/usr/bin/env bash
# test_endpoints.sh  —  Test the new O*NET/SOC endpoints
# Requires: curl, python3 (with json.tool for pretty-printing)
# Assumes the server is running at http://localhost:8000

BASE_URL="${1:-http://localhost:8000}"

echo ""
echo "=============================================="
echo " 1. POST /predict-soc  — basic prediction"
echo "=============================================="
curl -s "${BASE_URL}/predict-soc" \
  -H "Content-Type: application/json" \
  -d '{"skills":["Python","SQL","Machine Learning","Project Management"],"top_n":3}' \
  | python3 -m json.tool

echo ""
echo "=============================================="
echo " 2. POST /predict-soc  — with custom alpha"
echo "=============================================="
curl -s "${BASE_URL}/predict-soc" \
  -H "Content-Type: application/json" \
  -d '{"skills":["Python","Java","C++"],"top_n":5,"alpha":0.8,"include_all":true}' \
  | python3 -m json.tool

echo ""
echo "=============================================="
echo " 3. POST /predict-soc  — unknown skills only"
echo "=============================================="
curl -s "${BASE_URL}/predict-soc" \
  -H "Content-Type: application/json" \
  -d '{"skills":["Frobnication","Widget Smithing"],"top_n":3}' \
  | python3 -m json.tool

echo ""
echo "=============================================="
echo " 4. POST /adjacent-socs  — find adjacent SOCs"
echo "=============================================="
curl -s "${BASE_URL}/adjacent-socs" \
  -H "Content-Type: application/json" \
  -d '{"soc":"15-1132.00","top_n":5}' \
  | python3 -m json.tool

echo ""
echo "=============================================="
echo " 5. POST /adjacent-socs  — with user skills"
echo "=============================================="
curl -s "${BASE_URL}/adjacent-socs" \
  -H "Content-Type: application/json" \
  -d '{"soc":"15-1132.00","top_n":3,"skills":["Python","Kubernetes","AWS"]}' \
  | python3 -m json.tool

echo ""
echo "=============================================="
echo " 6. GET /soc/{code}  — SOC details"
echo "=============================================="
curl -s "${BASE_URL}/soc/15-1132.00" | python3 -m json.tool

echo ""
echo "=============================================="
echo " 7. GET /soc/{code}  — another SOC"
echo "=============================================="
curl -s "${BASE_URL}/soc/11-1011.00" | python3 -m json.tool

echo ""
echo "=============================================="
echo " Done."
echo "=============================================="
