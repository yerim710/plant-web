document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("loginForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const rememberMeCheckbox = document.getElementById("rememberMe");
  const loginMessage = document.getElementById("loginMessage");
  const forgotPasswordLink = document.getElementById("forgotPassword");
  const findPasswordModal = document.getElementById("findPasswordModal");
  const closeFindPasswordModal = document.getElementById(
    "closeFindPasswordModal"
  );
  const findEmailInput = document.getElementById("findEmail");
  const sendTempPasswordBtn = document.getElementById("sendTempPassword");
  const tempPasswordMessage = document.getElementById("tempPasswordMessage");

  // 저장된 이메일 불러오기
  const savedEmail = localStorage.getItem("savedEmail");
  if (savedEmail) {
    emailInput.value = savedEmail;
    rememberMeCheckbox.checked = true;
  }

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
    loginMessage.textContent = message;
    loginMessage.className = `message ${isError ? "error" : "success"}`;
    loginMessage.style.display = "block";
  };

  // 모달 메시지 표시 함수
  const showModalMessage = (message, isError = false) => {
    tempPasswordMessage.textContent = message;
    tempPasswordMessage.style.color = isError ? "red" : "green";
    tempPasswordMessage.style.display = "block";
  };

  // 비밀번호 찾기 모달 열기
  forgotPasswordLink.addEventListener("click", (e) => {
    e.preventDefault();
    findPasswordModal.style.display = "block";
  });

  // 비밀번호 찾기 모달 닫기
  closeFindPasswordModal.addEventListener("click", () => {
    findPasswordModal.style.display = "none";
    findEmailInput.value = "";
    tempPasswordMessage.style.display = "none";
  });

  // 모달 외부 클릭 시 닫기
  window.addEventListener("click", (e) => {
    if (e.target === findPasswordModal) {
      findPasswordModal.style.display = "none";
      findEmailInput.value = "";
      tempPasswordMessage.style.display = "none";
    }
  });

  // 임시 비밀번호 전송
  sendTempPasswordBtn.addEventListener("click", () => {
    const email = findEmailInput.value;

    if (!email) {
      showModalMessage("이메일을 입력해주세요.", true);
      return;
    }

    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showModalMessage("올바른 이메일 주소를 입력해주세요.", true);
      return;
    }

    // 사용자 확인
    const users = JSON.parse(localStorage.getItem("users") || "[]");
    const userIndex = users.findIndex((user) => user.email === email);

    if (userIndex === -1) {
      showModalMessage("등록되지 않은 이메일입니다.", true);
      return;
    }

    // 임시 비밀번호 생성 및 저장
    const tempPassword = generateTempPassword();
    users[userIndex].password = tempPassword;
    localStorage.setItem("users", JSON.stringify(users));

    // 임시 비밀번호 표시 (실제로는 이메일로 전송되어야 함)
    showModalMessage(
      `임시 비밀번호가 이메일로 전송되었습니다. (테스트용: ${tempPassword})`
    );
    sendTempPasswordBtn.disabled = true;
    sendTempPasswordBtn.textContent = "재전송";
  });

  // 로그인 처리
  loginForm.addEventListener("submit", (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const rememberMe = rememberMeCheckbox.checked;

    // 이메일 형식 검증
    if (!isValidEmail(email)) {
      showMessage("올바른 이메일 형식이 아닙니다.", true);
      return;
    }

    // 비밀번호 길이 검사
    if (password.length < 8) {
      showMessage("비밀번호는 8자 이상이어야 합니다.", true);
      return;
    }

    // 사용자 검증
    const users = JSON.parse(localStorage.getItem("users") || "[]");
    const user = users.find(
      (u) => u.email === email && u.password === password
    );

    if (user) {
      // 로그인 상태 저장
      localStorage.setItem("isLoggedIn", "true");
      localStorage.setItem("currentUser", JSON.stringify(user));

      // 로그인 상태 유지 처리
      if (rememberMe) {
        localStorage.setItem("savedEmail", email);
      } else {
        localStorage.removeItem("savedEmail");
      }

      showMessage("로그인 성공! 메인 페이지로 이동합니다.", "success");
      setTimeout(() => {
        window.location.href = "main.html";
      }, 1000);
    } else {
      showMessage("이메일 또는 비밀번호가 일치하지 않습니다.", true);
    }
  });

  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
});
