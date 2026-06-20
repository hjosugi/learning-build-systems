class Calculator {
  int add(int left, int right) {
    left + right
  }

  int divide(int left, int right) {
    if (right == 0) {
      throw new IllegalArgumentException("right must not be zero")
    }
    left.intdiv(right)
  }
}

