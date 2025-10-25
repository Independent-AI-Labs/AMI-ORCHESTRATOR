/**
 * Clean JavaScript code with no violations.
 */

function calculateSum(numbers) {
  return numbers.reduce((sum, num) => sum + num, 0);
}

function validateEmail(email) {
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return pattern.test(email);
}

module.exports = { calculateSum, validateEmail };
