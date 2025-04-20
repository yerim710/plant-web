document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("findPasswordForm");
  const emailInput = document.getElementById("email");
  const sendTempPasswordBtn = document.getElementById("sendTempPassword");
  const messageDiv = document.getElementById("message");

  // 임시 비밀번호 생성 함수
  const generateTempPassword = () => {
    const characters =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let password = "";
    for (let i = 0; i < 12; i++) {
      password += characters.charAt(
        Math.floor(Math.random() * characters.length)
      );
    }
    return password;
  };

  // 메시지 표시 함수
  const showMessage = (message, isError = false) => {
    messageDiv.textContent = message;
    messageDiv.style.color = isError ? "red" : "green";
    messageDiv.style.display = "block";
  };

  // 임시 비밀번호 전송
  sendTempPasswordBtn.addEventListener("click", () => {
    const email = emailInput.value;

    if (!email) {
      showMessage("이메일을 입력해주세요.", true);
      return;
    }

    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showMessage("올바른 이메일 주소를 입력해주세요.", true);
      return;
    }

    // 사용자 확인
    const users = JSON.parse(localStorage.getItem("users") || "[]");
    const userIndex = users.findIndex((user) => user.email === email);

    if (userIndex === -1) {
      showMessage("등록되지 않은 이메일입니다.", true);
      return;
    }

    // 임시 비밀번호 생성 및 저장
    const tempPassword = generateTempPassword();
    users[userIndex].password = tempPassword;
    localStorage.setItem("users", JSON.stringify(users));

    // 임시 비밀번호 표시 (실제로는 이메일로 전송되어야 함)
    showMessage(
      `임시 비밀번호가 이메일로 전송되었습니다. (테스트용: ${tempPassword})`
    );
    sendTempPasswordBtn.disabled = true;
    sendTempPasswordBtn.textContent = "재전송";
  });
});
