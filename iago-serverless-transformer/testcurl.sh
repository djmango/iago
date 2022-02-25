 curl --request POST \
  --url http://localhost:8080/2015-03-31/functions/function/invocations \
  --header 'Content-Type: application/json' \
  --data '{"strings":"[\"34ru9efhijzf9gu834u9ijtfgorfd08yuf0329weuv8hj43i2wfy80uejwpofdu890u40jfv08uydf0te2st\"]"}' | json_pp