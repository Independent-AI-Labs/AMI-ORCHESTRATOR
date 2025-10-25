/**
 * JavaScript code with known violations for testing.
 * All violations marked with exemption comments.
 */

function processData(data) {  // test-fixture
  try {
    return JSON.parse(data);
  } catch (e) {  // test-fixture
    console.log("Parse error:", e);  // test-fixture
    return null;  // test-fixture
  }
}

function buggyCode() {  // test-fixture
  var oldStyle = "should use let/const";  // test-fixture
  eval("dangerous code");  // test-fixture
  document.body.innerHTML = "<div>XSS risk</div>";  // test-fixture
}

module.exports = { processData, buggyCode };
