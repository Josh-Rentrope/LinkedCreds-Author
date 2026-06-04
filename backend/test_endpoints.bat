@echo off
REM test_endpoints.bat  —  Test the new O*NET/SOC endpoints (Windows)
REM Assumes the server is running at http://localhost:8000
REM Requires curl.exe (available on Windows 10/11 or via Git Bash)

set BASE_URL=http://127.0.0.1:8000
if not "%1"=="" set BASE_URL=%1

echo.
echo ==============================================
echo  1. POST /predict-soc  -- basic prediction
echo ==============================================
curl -s "%BASE_URL%/predict-soc" -H "Content-Type: application/json" -d "{\"skills\":[\"Python\",\"SQL\",\"Machine Learning\",\"Project Management\"],\"top_n\":3}"
echo.

echo.
echo ==============================================
echo  2. POST /predict-soc  -- with custom alpha
echo ==============================================
curl -s "%BASE_URL%/predict-soc" -H "Content-Type: application/json" -d "{\"skills\":[\"Python\",\"Java\",\"C++\"],\"top_n\":5,\"alpha\":0.8,\"include_all\":true}"
echo.

echo.
echo ==============================================
echo  3. POST /adjacent-socs  -- find adjacent SOCs
echo ==============================================
curl -s "%BASE_URL%/adjacent-socs" -H "Content-Type: application/json" -d "{\"soc\":\"15-1132.00\",\"top_n\":5}"
echo.

echo.
echo ==============================================
echo  4. POST /adjacent-socs  -- with user skills
echo ==============================================
curl -s "%BASE_URL%/adjacent-socs" -H "Content-Type: application/json" -d "{\"soc\":\"15-1132.00\",\"top_n\":3,\"skills\":[\"Python\",\"Kubernetes\",\"AWS\"]}"
echo.

echo.
echo ==============================================
echo  5. GET /soc/{code}  -- SOC details
echo ==============================================
curl -s "%BASE_URL%/soc/15-1132.00"
echo.

echo.
echo ==============================================
echo  Done.
echo ==============================================
