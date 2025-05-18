document.addEventListener("DOMContentLoaded", function () {
  // 현재 로그인한 사용자의 이메일을 가져와서 표시
  fetch("/api/current-user")
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        document.getElementById("email").value = data.email;
      } else {
        window.location.href = "/login";
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      window.location.href = "/login";
    });

  // 폼 제출 처리
  document
    .getElementById("adminVerificationForm")
    .addEventListener("submit", function (e) {
      e.preventDefault();

      const formData = {
        email: document.getElementById("email").value,
        businessNumber: document.getElementById("businessNumber").value,
        officePhone: document.getElementById("officePhone").value,
        managerPhone: document.getElementById("managerPhone").value,
        faxNumber: document.getElementById("faxNumber").value,
        address: document.getElementById("address").value,
        representativeName: document.getElementById("representativeName").value,
        mobilePhone: document.getElementById("mobilePhone").value,
      };

      fetch("/api/admin-verification", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            alert("관리자 인증 신청이 완료되었습니다.");
            window.location.href = "/login";
          } else {
            alert(data.message || "관리자 인증 신청에 실패했습니다.");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("서버 오류가 발생했습니다.");
        });
    });
});
