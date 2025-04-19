document.addEventListener("DOMContentLoaded", () => {
  const mainContainer = document.querySelector(".main-container");
  const openVolunteerFormBtn = document.getElementById("openVolunteerFormBtn");
  const volunteerModal = document.getElementById("volunteerModal");
  const closeModalBtn = document.getElementById("closeModal");
  const volunteerForm = document.getElementById("volunteerForm");
  const volunteerList = document.getElementById("volunteerList");
  const logoutBtn = document.getElementById("logoutBtn");
  const deleteAccountBtn = document.getElementById("deleteAccountBtn");
  const searchAddressBtn = document.getElementById("searchAddress");
  const locationInput = document.getElementById("location");
  const locationDetailInput = document.getElementById("locationDetail");
  const profileBtn = document.getElementById("profileBtn");
  const profileModal = document.getElementById("profileModal");
  const closeProfileModal = document.getElementById("closeProfileModal");
  const profileEmail = document.getElementById("profileEmail");
  const changePasswordBtn = document.getElementById("changePasswordBtn");
  const passwordModal = document.getElementById("passwordModal");
  const closePasswordModal = document.getElementById("closePasswordModal");
  const passwordForm = document.getElementById("passwordForm");
  const imageInput = document.getElementById("image");
  const imagePreview = document.getElementById("imagePreview");
  const boardBtn = document.getElementById("boardBtn");

  let editingIndex = -1; // 수정 중인 봉사활동의 인덱스

  // 메시지 표시 함수
  const showMessage = (message) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = "message";
    messageDiv.textContent = message;
    document.body.appendChild(messageDiv);

    // 1초 후 메시지 제거
    setTimeout(() => {
      messageDiv.remove();
    }, 1000);
  };

  // 주소 검색
  searchAddressBtn.addEventListener("click", () => {
    new daum.Postcode({
      oncomplete: function (data) {
        let addr = "";
        let extraAddr = "";

        if (data.userSelectedType === "R") {
          addr = data.roadAddress;
        } else {
          addr = data.jibunAddress;
        }

        if (data.userSelectedType === "R") {
          if (data.bname !== "" && /[동|로|가]$/g.test(data.bname)) {
            extraAddr += data.bname;
          }
          if (data.buildingName !== "" && data.apartment === "Y") {
            extraAddr +=
              extraAddr !== "" ? ", " + data.buildingName : data.buildingName;
          }
          if (extraAddr !== "") {
            extraAddr = " (" + extraAddr + ")";
          }
        }

        locationInput.value = addr + extraAddr;
        locationDetailInput.focus();
      },
    }).open();
  });

  // 모달 열기
  openVolunteerFormBtn.addEventListener("click", () => {
    editingIndex = -1;
    volunteerForm.reset();
    volunteerModal.style.display = "block";
  });

  // 모달 닫기
  closeModalBtn.addEventListener("click", () => {
    volunteerModal.style.display = "none";
    volunteerForm.reset();
    editingIndex = -1;
  });

  // 모달 외부 클릭 시 닫기
  window.addEventListener("click", (e) => {
    if (e.target === volunteerModal) {
      volunteerModal.style.display = "none";
      volunteerForm.reset();
      editingIndex = -1;
    }
  });

  // 이미지 미리보기
  imageInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
        imagePreview.style.display = "block";
      };
      reader.readAsDataURL(file);
    }
  });

  // 봉사활동 등록/수정 처리
  volunteerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("title", document.getElementById("title").value);
    formData.append("hours", document.getElementById("hours").value);
    formData.append("days", document.getElementById("days").value);
    formData.append("target", document.getElementById("target").value);
    formData.append("location", document.getElementById("location").value);
    formData.append(
      "locationDetail",
      document.getElementById("locationDetail").value
    );
    formData.append("details", document.getElementById("details").value);
    formData.append("start_date", document.getElementById("start_date").value);
    formData.append("end_date", document.getElementById("end_date").value);

    // 시작일과 종료일 유효성 검사
    const startDate = new Date(document.getElementById("start_date").value);
    const endDate = new Date(document.getElementById("end_date").value);

    if (startDate > endDate) {
      showMessage("종료일은 시작일보다 늦어야 합니다.", true);
      return;
    }

    // 이미지 파일 추가
    const imageFile = imageInput.files[0];
    if (imageFile) {
      formData.append("image", imageFile);
    }

    try {
      const response = await fetch("http://localhost:5000/api/volunteer", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        showMessage("봉사활동이 등록되었습니다.");
        volunteerModal.style.display = "none";
        volunteerForm.reset();
        imagePreview.style.display = "none";
        loadVolunteerList();
      } else {
        showMessage(data.message || "봉사활동 등록에 실패했습니다.", true);
      }
    } catch (error) {
      console.error("Error:", error);
      showMessage("봉사활동 등록 중 오류가 발생했습니다.", true);
    }
  });

  // 봉사활동 화면에 표시
  const displayVolunteer = (volunteer, index) => {
    const volunteerElement = document.createElement("div");
    volunteerElement.className = "volunteer-item";

    // 날짜 포맷팅 함수
    const formatDate = (dateString) => {
      const date = new Date(dateString);
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    };

    volunteerElement.innerHTML = `
            <h3>${volunteer.title}</h3>
            ${
              volunteer.image_path
                ? `<div class="volunteer-image"><img src="${volunteer.image_path}" alt="봉사 사진"></div>`
                : ""
            }
            <div class="volunteer-info">
                <div class="info-group">
                    <label>봉사 장소</label>
                    <div>${volunteer.location}</div>
                </div>
                <div class="info-group">
                    <label>봉사 시간</label>
                    <div>${volunteer.hours}시간</div>
                </div>
                <div class="info-group">
                    <label>활동 요일</label>
                    <div>${volunteer.days}</div>
                </div>
                <div class="info-group">
                    <label>봉사 대상</label>
                    <div>${volunteer.target}</div>
                </div>
                <div class="info-group">
                    <label>활동 기간</label>
                    <div>${formatDate(volunteer.start_date)} ~ ${formatDate(
      volunteer.end_date
    )}</div>
                </div>
            </div>
            <div class="details">
                <label>상세 내용</label>
                <div>${volunteer.details}</div>
            </div>
            <div class="volunteer-actions">
                <button class="edit-btn" data-index="${index}">수정</button>
                <button class="delete-btn" data-index="${index}">삭제</button>
            </div>
        `;

    // 수정 버튼 이벤트 리스너 추가
    const editBtn = volunteerElement.querySelector(".edit-btn");
    editBtn.addEventListener("click", () => {
      editingIndex = index;
      document.getElementById("title").value = volunteer.title;
      locationInput.value = volunteer.location;
      document.getElementById("hours").value = volunteer.hours;
      document.getElementById("days").value = volunteer.days;
      document.getElementById("target").value = volunteer.target;
      document.getElementById("details").value = volunteer.details;
      document.getElementById("start_date").value = volunteer.start_date;
      document.getElementById("end_date").value = volunteer.end_date;
      volunteerModal.style.display = "block";
    });

    // 삭제 버튼 이벤트 리스너 추가
    const deleteBtn = volunteerElement.querySelector(".delete-btn");
    deleteBtn.addEventListener("click", () => {
      if (confirm("정말로 이 봉사활동을 삭제하시겠습니까?")) {
        const volunteers = JSON.parse(
          localStorage.getItem("volunteers") || "[]"
        );
        volunteers.splice(index, 1);
        localStorage.setItem("volunteers", JSON.stringify(volunteers));
        volunteerList.innerHTML = "";
        loadVolunteers();
      }
    });

    volunteerList.appendChild(volunteerElement);
  };

  // 저장된 봉사활동 목록 불러오기
  const loadVolunteers = () => {
    const volunteers = JSON.parse(localStorage.getItem("volunteers") || "[]");
    volunteers.forEach((volunteer, index) => {
      displayVolunteer(volunteer, index);
    });
  };

  // 로그아웃 처리
  logoutBtn.addEventListener("click", () => {
    if (confirm("정말로 로그아웃 하시겠습니까?")) {
      localStorage.removeItem("isLoggedIn");
      localStorage.removeItem("currentUser");
      showMessage("로그아웃되었습니다. 로그인 페이지로 이동합니다.");
      setTimeout(() => {
        window.location.href = "login.html";
      }, 1000);
    }
  });

  // 회원탈퇴 처리
  deleteAccountBtn.addEventListener("click", () => {
    const secondConfirm = confirm(
      "정말로 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없으며, 모든 데이터가 삭제됩니다."
    );
    if (secondConfirm) {
      const currentUser = JSON.parse(localStorage.getItem("currentUser"));
      const users = JSON.parse(localStorage.getItem("users") || "[]");

      // 현재 사용자 정보 제거
      const updatedUsers = users.filter(
        (user) => user.email !== currentUser.email
      );
      localStorage.setItem("users", JSON.stringify(updatedUsers));

      // 로그인 상태 및 사용자 정보 제거
      localStorage.removeItem("isLoggedIn");
      localStorage.removeItem("currentUser");

      showMessage("회원탈퇴가 완료되었습니다. 로그인 페이지로 이동합니다.");
      setTimeout(() => {
        window.location.href = "login.html";
      }, 1000);
    }
  });

  // 프로필 모달 열기
  profileBtn.addEventListener("click", () => {
    // 프로필 모달 표시
    profileModal.style.display = "block";
    // 현재 로그인한 사용자의 이메일 표시
    const currentUser = JSON.parse(localStorage.getItem("currentUser"));
    if (currentUser) {
      profileEmail.textContent = currentUser.email;
    }
  });

  // 프로필 모달 닫기
  closeProfileModal.addEventListener("click", () => {
    profileModal.style.display = "none";
  });

  // 비밀번호 변경 모달 열기
  changePasswordBtn.addEventListener("click", () => {
    profileModal.style.display = "none";
    passwordModal.style.display = "block";
  });

  // 비밀번호 변경 모달 닫기
  closePasswordModal.addEventListener("click", () => {
    passwordModal.style.display = "none";
    passwordForm.reset();
  });

  // 비밀번호 변경 처리
  passwordForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const currentPassword = document.getElementById("currentPassword").value;
    const newPassword = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    const currentUser = JSON.parse(localStorage.getItem("currentUser"));
    const users = JSON.parse(localStorage.getItem("users") || "[]");

    // 현재 비밀번호 확인
    if (currentPassword !== currentUser.password) {
      alert("현재 비밀번호가 일치하지 않습니다.");
      return;
    }

    // 새 비밀번호 확인
    if (newPassword !== confirmPassword) {
      alert("새 비밀번호가 일치하지 않습니다.");
      return;
    }

    // 비밀번호 변경
    const userIndex = users.findIndex(
      (user) => user.email === currentUser.email
    );
    users[userIndex].password = newPassword;
    currentUser.password = newPassword;

    localStorage.setItem("users", JSON.stringify(users));
    localStorage.setItem("currentUser", JSON.stringify(currentUser));

    alert("비밀번호가 변경되었습니다.");
    passwordModal.style.display = "none";
    passwordForm.reset();
  });

  // 게시판 버튼 클릭 이벤트
  boardBtn.addEventListener("click", () => {
    window.location.href = "board.html";
  });

  // 봉사활동 목록 불러오기
  async function loadVolunteerList() {
    try {
      const response = await fetch("http://localhost:5000/api/volunteers");
      const data = await response.json();

      if (data.success) {
        const volunteerList = document.getElementById("volunteerList");
        volunteerList.innerHTML = ""; // 기존 목록 초기화

        data.volunteers.forEach((volunteer) => {
          const volunteerElement = document.createElement("div");
          volunteerElement.className = "volunteer-item";

          volunteerElement.innerHTML = `
            <h3>${volunteer.title}</h3>
            ${
              volunteer.image_path
                ? `<div class="volunteer-image"><img src="${volunteer.image_path}" alt="봉사 사진"></div>`
                : ""
            }
            <div class="volunteer-info">
              <div class="info-group">
                <label>봉사 장소</label>
                <div>${volunteer.location} ${
            volunteer.locationDetail || ""
          }</div>
              </div>
              <div class="info-group">
                <label>봉사 시간</label>
                <div>${volunteer.hours}시간</div>
              </div>
              <div class="info-group">
                <label>활동 요일</label>
                <div>${volunteer.days}</div>
              </div>
              <div class="info-group">
                <label>봉사 대상</label>
                <div>${volunteer.target}</div>
              </div>
            </div>
            <div class="details">
              <label>상세 내용</label>
              <div>${volunteer.details}</div>
            </div>
            <div class="volunteer-actions">
              <button class="edit-btn" data-id="${volunteer.id}">수정</button>
              <button class="delete-btn" data-id="${volunteer.id}">삭제</button>
            </div>
          `;

          // 수정 버튼 이벤트 리스너
          const editBtn = volunteerElement.querySelector(".edit-btn");
          editBtn.addEventListener("click", () => {
            // 수정 폼에 데이터 채우기
            document.getElementById("title").value = volunteer.title;
            document.getElementById("hours").value = volunteer.hours;
            document.getElementById("days").value = volunteer.days;
            document.getElementById("target").value = volunteer.target;
            document.getElementById("location").value = volunteer.location;
            document.getElementById("locationDetail").value =
              volunteer.locationDetail || "";
            document.getElementById("details").value = volunteer.details;

            // 이미지 미리보기 업데이트
            if (volunteer.image_path) {
              imagePreview.src = volunteer.image_path;
              imagePreview.style.display = "block";
            }

            // 모달 표시
            volunteerModal.style.display = "block";
          });

          // 삭제 버튼 이벤트 리스너
          const deleteBtn = volunteerElement.querySelector(".delete-btn");
          deleteBtn.addEventListener("click", async () => {
            if (confirm("정말 이 봉사활동을 삭제하시겠습니까?")) {
              try {
                const response = await fetch(
                  `http://localhost:5000/api/volunteers/${volunteer.id}`,
                  {
                    method: "DELETE",
                  }
                );

                const data = await response.json();
                if (data.success) {
                  showMessage("봉사활동이 삭제되었습니다.");
                  loadVolunteerList(); // 목록 새로고침
                } else {
                  showMessage(data.message || "삭제에 실패했습니다.", true);
                }
              } catch (error) {
                console.error("Error:", error);
                showMessage("삭제 중 오류가 발생했습니다.", true);
              }
            }
          });

          volunteerList.appendChild(volunteerElement);
        });
      } else {
        showMessage(
          data.message || "봉사활동 목록을 불러오는데 실패했습니다.",
          true
        );
      }
    } catch (error) {
      console.error("Error:", error);
      showMessage("봉사활동 목록을 불러오는 중 오류가 발생했습니다.", true);
    }
  }

  // 페이지 로드 시 봉사활동 목록 불러오기
  loadVolunteerList();
});
