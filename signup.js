document.addEventListener("DOMContentLoaded", () => {
  const signupForm = document.getElementById("signupForm");
  const nameInput = document.getElementById("name");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const verificationDiv = document.getElementById("verification");
  const verificationInputs = document.querySelectorAll(
    ".verification-code-input"
  );
  const sendVerificationBtn = document.getElementById("sendVerification");
  const confirmVerificationBtn = document.getElementById(
    "confirmVerificationBtn"
  );

  let isEmailVerified = false;

  // 필수 요소들이 존재하는지 확인
  if (
    !signupForm ||
    !nameInput ||
    !emailInput ||
    !passwordInput ||
    !confirmPasswordInput ||
    !verificationDiv ||
    !verificationInputs ||
    !sendVerificationBtn ||
    !confirmVerificationBtn
  ) {
    console.error("필수 요소를 찾을 수 없습니다.");
    return;
  }

  // 이름 유효성 검사
  const validateName = (name) => {
    return name.length >= 2;
  };

  // 이메일 유효성 검사
  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // 비밀번호 유효성 검사
  const validatePassword = (password) => {
    return password.length >= 6;
  };

  // 인증 코드 전송
  sendVerificationBtn.addEventListener("click", async () => {
    const email = emailInput.value.trim();

    if (!validateEmail(email)) {
      alert("올바른 이메일 형식이 아닙니다.");
      return;
    }

    try {
      const response = await fetch(
        "http://localhost:5000/api/send-verification",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }),
        }
      );

      const data = await response.json();

      if (data.success) {
        alert("인증 코드가 이메일로 전송되었습니다.");
        verificationDiv.style.display = "block";
        verificationInputs[0].focus();
      } else {
        alert(data.message || "인증 코드 전송에 실패했습니다.");
      }
    } catch (error) {
      console.error("인증 코드 전송 오류:", error);
      alert("인증 코드 전송에 실패했습니다.");
    }
  });

  // 인증 코드 입력 필드의 이벤트 리스너 추가
  verificationInputs.forEach((input, index) => {
    input.addEventListener("input", (e) => {
      const value = e.target.value;
      if (value.length === 1 && index < verificationInputs.length - 1) {
        verificationInputs[index + 1].focus();
      }
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !e.target.value && index > 0) {
        verificationInputs[index - 1].focus();
      }
    });
  });

  // 인증 코드 확인
  confirmVerificationBtn.addEventListener("click", async () => {
    const email = emailInput.value.trim();
    const code = Array.from(verificationInputs)
      .map((input) => input.value)
      .join("");

    if (code.length !== 6) {
      alert("인증 코드 6자리를 모두 입력해주세요.");
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/api/verify-code", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, code }),
      });

      const data = await response.json();

      if (data.success) {
        alert("이메일 인증이 완료되었습니다.");
        isEmailVerified = true;
        verificationInputs.forEach((input) => (input.disabled = true));
        confirmVerificationBtn.disabled = true;
      } else {
        alert(data.message || "인증 코드가 일치하지 않습니다.");
      }
    } catch (error) {
      console.error("인증 코드 확인 오류:", error);
      alert("인증 코드 확인에 실패했습니다.");
    }
  });

  // 폼 제출 이벤트
  signupForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const name = nameInput.value;
    const email = emailInput.value;
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    // 유효성 검사
    if (!validateName(name)) {
      alert("이름은 최소 2자 이상이어야 합니다.");
      return;
    }

    if (!validateEmail(email)) {
      alert("올바른 이메일 주소를 입력해주세요.");
      return;
    }

    if (!validatePassword(password)) {
      alert("비밀번호는 최소 6자 이상이어야 합니다.");
      return;
    }

    if (password !== confirmPassword) {
      alert("비밀번호가 일치하지 않습니다.");
      return;
    }

    if (!isEmailVerified) {
      alert("이메일 인증이 필요합니다.");
      return;
    }

    try {
      // Flask 서버로 회원가입 데이터 전송
      const response = await fetch("http://localhost:5000/api/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name,
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (data.success) {
        alert(data.message);
        // 회원가입 성공 시 로그인 페이지로 이동
        window.location.href = "login.html";
      } else {
        alert(data.message);
      }
    } catch (error) {
      console.error("Error:", error);
      alert("회원가입 중 오류가 발생했습니다.");
    }
  });
});
