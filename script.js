document.addEventListener("DOMContentLoaded", () => {
  // 요소 선택
  const form = document.getElementById("signupForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const messageDiv = document.getElementById("message");
  const verificationDiv = document.getElementById("verification");
  const verificationInput = document.getElementById("verificationCode");
  const sendVerificationBtn = document.getElementById("sendVerification");
  const submitBtn = document.getElementById("submitBtn");

  let verificationCode = "";
  let isEmailVerified = false;

  // 이메일 형식 검증
  const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // 비밀번호 형식 검증
  const isValidPassword = (password) => {
    return password.length >= 8;
  };

  // 메시지 표시 함수
  const showMessage = (message, isError = false) => {
    messageDiv.textContent = message;
    messageDiv.style.color = isError ? "red" : "green";
    messageDiv.style.display = "block";
  };

  // 인증번호 생성 함수
  const generateVerificationCode = () => {
    const characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "";
    for (let i = 0; i < 6; i++) {
      code += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return code;
  };

  // 인증번호 전송
  sendVerificationBtn.addEventListener("click", () => {
    const email = emailInput.value;

    if (!isValidEmail(email)) {
      showMessage("올바른 이메일 주소를 입력해주세요.", true);
      return;
    }

    // 이메일 중복 체크
    const users = JSON.parse(localStorage.getItem("users") || "[]");
    if (users.some((user) => user.email === email)) {
      showMessage("이미 등록된 이메일입니다.", true);
      return;
    }

    // 인증번호 생성 및 저장
    verificationCode = generateVerificationCode();
    localStorage.setItem("verificationCode", verificationCode);
    localStorage.setItem("verificationEmail", email);
    localStorage.setItem("verificationExpiry", Date.now() + 300000); // 5분 유효

    // 인증번호 표시 (실제로는 이메일로 전송되어야 함)
    showMessage(
      `인증번호가 이메일로 전송되었습니다. (테스트용: ${verificationCode})`
    );
    verificationDiv.style.display = "block";
    sendVerificationBtn.disabled = true;
    sendVerificationBtn.textContent = "재전송";
  });

  // 인증번호 확인
  verificationInput.addEventListener("input", () => {
    const inputCode = verificationInput.value.toUpperCase();
    const storedCode = localStorage.getItem("verificationCode");
    const storedEmail = localStorage.getItem("verificationEmail");
    const expiryTime = localStorage.getItem("verificationExpiry");

    if (Date.now() > expiryTime) {
      showMessage("인증번호가 만료되었습니다. 다시 전송해주세요.", true);
      verificationDiv.style.display = "none";
      sendVerificationBtn.disabled = false;
      sendVerificationBtn.textContent = "인증번호 전송";
      return;
    }

    if (emailInput.value !== storedEmail) {
      showMessage("이메일이 일치하지 않습니다.", true);
      return;
    }

    if (inputCode === storedCode) {
      isEmailVerified = true;
      showMessage("이메일 인증이 완료되었습니다.");
      verificationInput.disabled = true;
      sendVerificationBtn.disabled = true;
    } else {
      isEmailVerified = false;
      showMessage("잘못된 인증번호입니다.", true);
    }
  });

  // 폼 제출 처리
  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const email = emailInput.value;
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    // 기본 검증
    if (!isValidEmail(email)) {
      showMessage("올바른 이메일 주소를 입력해주세요.", true);
      return;
    }

    if (!isValidPassword(password)) {
      showMessage("비밀번호는 8자 이상이어야 합니다.", true);
      return;
    }

    if (password !== confirmPassword) {
      showMessage("비밀번호가 일치하지 않습니다.", true);
      return;
    }

    // 이메일 인증 확인
    if (!isEmailVerified) {
      showMessage("이메일 인증을 완료해주세요.", true);
      return;
    }

    // 이메일 중복 체크
    const users = JSON.parse(localStorage.getItem("users") || "[]");
    if (users.some((user) => user.email === email)) {
      showMessage("이미 등록된 이메일입니다.", true);
      return;
    }

    // 사용자 정보 저장
    users.push({
      email,
      password,
      date: new Date().toISOString(),
    });
    localStorage.setItem("users", JSON.stringify(users));

    // 인증 관련 정보 삭제
    localStorage.removeItem("verificationCode");
    localStorage.removeItem("verificationEmail");
    localStorage.removeItem("verificationExpiry");

    showMessage("회원가입이 완료되었습니다. 로그인 페이지로 이동합니다.");
    setTimeout(() => {
      window.location.href = "login.html";
    }, 2000);
  });
});
