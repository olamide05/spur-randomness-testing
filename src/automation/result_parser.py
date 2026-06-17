def create_result_template(dataset_name):
    return {
        "dataset": dataset_name,
        "tests": {},
        "summary": {}
    }
def add_test_result(
    results,
    test_name,
    p_value,
    passed
):
    results["tests"][test_name] = {
        "p_value": p_value,
        "passed": passed
    }
result = create_result_template("sample.txt")
add_test_result(result, "test1", 0.05, True)
print(result)