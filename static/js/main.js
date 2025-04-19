// 클라우드 서버 주소
const API_BASE_URL = "http://35.232.136.23:5000";

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  let currentUser = null; // 현재 사용자 정보를 저장할 변수

  // 사용자 정보 로드 함수
  async function loadUserInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/current-user`); // 수정
      const data = await response.json();

      if (data.success) {
        currentUser = data; // 현재 사용자 정보 저장
        displayUserInfo(data);
        checkAdminVerification(data);
      } else {
        console.error("사용자 정보 로드 실패:", data.message);
        // 로그인 페이지로 리디렉션 또는 다른 처리
        window.location.href = "/login";
      }
    } catch (error) {
      console.error("사용자 정보 로드 중 오류:", error);
      // 로그인 페이지로 리디렉션 또는 다른 처리
      window.location.href = "/login";
    }
  }

  // 사용자 정보 표시 함수
  function displayUserInfo(userData) {
    const userNameElement = document.getElementById("userName");
    const userEmailElement = document.getElementById("userEmail");
    const adminStatusElement = document.getElementById("adminStatus");

    if (userNameElement) userNameElement.textContent = userData.name;
    if (userEmailElement) userEmailElement.textContent = userData.email;
    if (adminStatusElement) {
      adminStatusElement.textContent = userData.is_admin
        ? "관리자 인증 완료"
        : "관리자 인증 필요";
    }
  }

  // 관리자 인증 확인 및 처리 함수
  function checkAdminVerification(userData) {
    const registerVolunteerBtn = document.getElementById(
      "registerVolunteerBtn"
    );
    const adminVerificationModal = document.getElementById(
      "adminVerificationModal"
    );
    const confirmVerificationBtn = document.getElementById(
      "confirmVerificationBtn"
    );
    const cancelVerificationBtn = document.getElementById(
      "cancelVerificationBtn"
    );

    if (registerVolunteerBtn) {
      registerVolunteerBtn.addEventListener("click", (e) => {
        e.preventDefault(); // 기본 동작(페이지 이동) 방지
        if (userData && userData.is_admin) {
          // 관리자 인증 완료 시 봉사 등록 페이지로 이동
          window.location.href = "/register-volunteer";
        } else {
          // 관리자 인증 미완료 시 모달 표시
          if (adminVerificationModal) {
            adminVerificationModal.style.display = "block";
          }
        }
      });
    }

    // 모달 내 '예' 버튼 클릭 시
    if (confirmVerificationBtn) {
      confirmVerificationBtn.addEventListener("click", () => {
        window.location.href = "/admin-verification"; // 관리자 인증 페이지로 이동
      });
    }

    // 모달 내 '아니오' 버튼 클릭 시
    if (cancelVerificationBtn) {
      cancelVerificationBtn.addEventListener("click", () => {
        if (adminVerificationModal) {
          adminVerificationModal.style.display = "none"; // 모달 닫기
        }
      });
    }

    // 모달 외부 클릭 시 닫기 (선택 사항)
    if (adminVerificationModal) {
      adminVerificationModal.addEventListener("click", (event) => {
        if (event.target === adminVerificationModal) {
          adminVerificationModal.style.display = "none";
        }
      });
    }
  }

  // 로그아웃 버튼 처리
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/logout`, {
          method: "POST",
        }); // 수정
        if (response.ok) {
          localStorage.removeItem("token"); // 토큰 삭제
          window.location.href = "/login"; // 로그인 페이지로 이동
        } else {
          console.error("로그아웃 실패");
          alert("로그아웃에 실패했습니다.");
        }
      } catch (error) {
        console.error("로그아웃 중 오류:", error);
        alert("로그아웃 중 오류가 발생했습니다.");
      }
    });
  }

  // 봉사활동 목록 로드 함수
  async function loadVolunteers() {
    const volunteerListElement = document.getElementById("volunteerList");
    if (!volunteerListElement) return; // 목록 요소 없으면 종료

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/volunteers?sort=duration`
      ); // 수정 (정렬 파라미터 추가 예시)
      const data = await response.json();

      if (data.success && data.volunteers) {
        volunteerListElement.innerHTML = ""; // 기존 목록 비우기
        if (data.volunteers.length === 0) {
          volunteerListElement.innerHTML = "<p>등록된 봉사활동이 없습니다.</p>";
        } else {
          data.volunteers.forEach((volunteer) => {
            const card = createVolunteerCard(volunteer);
            volunteerListElement.appendChild(card);
          });
        }
      } else {
        console.error("봉사활동 목록 로드 실패:", data.message);
        volunteerListElement.innerHTML =
          "<p>봉사활동 목록을 불러오는 데 실패했습니다.</p>";
      }
    } catch (error) {
      console.error("봉사활동 목록 로드 중 오류:", error);
      volunteerListElement.innerHTML =
        "<p>봉사활동 목록 로드 중 오류가 발생했습니다.</p>";
    }
  }

  // 봉사활동 카드 생성 함수 (개선된 버전)
  function createVolunteerCard(volunteer) {
    const card = document.createElement("div");
    card.className = "volunteer-card"; // 스타일링을 위한 클래스

    // 이미지 경로 처리 (기본 이미지 또는 실제 이미지)
    const imagePath = volunteer.image_path
      ? `${API_BASE_URL}/static/${volunteer.image_path}` // 수정: 이미지 경로도 서버 주소 필요
      : "/static/images/default_volunteer.jpg"; // 기본 이미지 경로

    card.innerHTML = `
        <img src="${imagePath}" alt="${
      volunteer.title || "봉사활동"
    }" class="volunteer-image">
        <div class="volunteer-info">
            <h3>${volunteer.title || "제목 없음"}</h3>
            <p><strong>기간:</strong> ${volunteer.start_date || "미정"} ~ ${
      volunteer.end_date || "미정"
    }</p>
            <p><strong>장소:</strong> ${volunteer.location || "장소 미정"} ${
      volunteer.locationDetail ? `(${volunteer.locationDetail})` : ""
    }</p>
            <p><strong>대상:</strong> ${volunteer.target || "대상 미정"}</p>
            <p><strong>요일:</strong> ${volunteer.days || "요일 미정"}</p>
            <p><strong>시간:</strong> ${
              volunteer.hours ? `${volunteer.hours} 시간` : "시간 미정"
            }</p>
            <p><strong>세부 정보:</strong> ${
              volunteer.details || "세부 정보 없음"
            }</p>
            <button class="apply-btn" data-volunteer-id="${
              volunteer.id
            }">신청하기</button>
        </div>
    `;

    // 신청하기 버튼 이벤트 리스너 추가 (API 호출 필요)
    const applyBtn = card.querySelector(".apply-btn");
    if (applyBtn) {
      applyBtn.addEventListener("click", async (e) => {
        const volunteerId = e.target.getAttribute("data-volunteer-id");
        if (!currentUser) {
          alert("사용자 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
          return;
        }
        if (confirm(`'${volunteer.title}' 봉사활동에 신청하시겠습니까?`)) {
          // 여기에 봉사 신청 API 호출 로직 추가
          try {
            const applyResponse = await fetch(
              `${API_BASE_URL}/api/volunteer/apply`,
              {
                // 수정: API 엔드포인트 확인 필요
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  // 인증 토큰 등 필요시 헤더 추가
                  // 'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                  volunteer_id: volunteerId,
                  user_id: currentUser.id,
                }), // 서버에서 세션 ID를 사용한다면 user_id 불필요
              }
            );
            const applyData = await applyResponse.json();
            if (applyData.success) {
              alert("봉사활동 신청이 완료되었습니다.");
              // 필요하다면 신청 버튼 비활성화 또는 UI 변경
            } else {
              alert(applyData.message || "봉사활동 신청에 실패했습니다.");
            }
          } catch (applyError) {
            console.error("봉사 신청 중 오류:", applyError);
            alert("봉사 신청 중 오류가 발생했습니다.");
          }
        }
      });
    }

    return card;
  }

  // 초기화: 사용자 정보 로드 후 봉사활동 목록 로드
  async function initializePage() {
    await loadUserInfo();
    if (document.getElementById("volunteerList")) {
      // main.html에만 목록 로드
      loadVolunteers();
    }
  }

  initializePage();
});
