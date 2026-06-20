evaluate(new File("projects/groovy-unit-test-lab/Calculator.groovy"))

def calculator = new Calculator()

assert calculator.add(2, 3) == 5
assert calculator.divide(9, 3) == 3

try {
  calculator.divide(1, 0)
  assert false: "expected divide by zero to fail"
} catch (IllegalArgumentException expected) {
  assert expected.message.contains("zero")
}

println "ok"
