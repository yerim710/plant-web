// 로컬 테스트용 API 주소
const API_BASE_URL = "";

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOMContentLoaded event fired"); // 로그 추가
  const token = localStorage.getItem("token");
  let currentUser = null; // 현재 사용자 정보를 저장할 변수

  // 사용자 정보 로드 함수
  async function loadUserInfo() {
    console.log("loadUserInfo started"); // 로그 추가
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/current-user` /*, {
        // headers: { 
        //   Accept: "application/json", // Accept 헤더 임시 제거
        // },
      }*/
      );
      console.log("API fetch completed, status:", response.status); // 로그 추가

      // 응답 상태 코드 확인 추가
      if (!response.ok) {
        console.error("사용자 정보 로드 실패 (상태 코드):", response.status);
        if (response.status === 401 || response.status === 404) {
          console.log("Redirecting to /login due to status 401/404"); // 로그 추가
          window.location.href = "/login";
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // JSON 파싱 분리 및 로그 추가
      let data;
      try {
        data = await response.json();
        console.log("API response JSON parsed:", data); // 로그 추가
      } catch (jsonError) {
        console.error("Failed to parse JSON response:", jsonError);
        console.log("Redirecting to /login due to JSON parse error"); // 로그 추가
        window.location.href = "/login";
        return;
      }

      // data.success 확인 및 로그 추가
      if (data.success) {
        console.log("API success: true. Updating UI."); // 로그 추가
        currentUser = data; // 현재 사용자 정보 저장
        displayUserInfo(data);
        checkAdminVerification(data);
      } else {
        console.error("API success: false. Message:", data.message);
        console.log("Redirecting to /login because data.success is false"); // 로그 추가
        window.location.href = "/login";
      }
    } catch (error) {
      console.error("사용자 정보 로드 중 오류 (catch block):", error);
      console.log("Redirecting to /login due to catch block error"); // 로그 추가
      window.location.href = "/login";
    }
    console.log("loadUserInfo finished"); // 로그 추가 (리다이렉션 없을 때만 보임)
  }

  // 사용자 정보 표시 함수
  function displayUserInfo(userData) {
    const userNameElement = document.getElementById("userName");
    const userEmailElement = document.getElementById("userEmail");

    if (userNameElement) userNameElement.textContent = userData.name;
    if (userEmailElement) userEmailElement.textContent = userData.email;
  }

  // 관리자 인증 확인 및 처리 함수
  function checkAdminVerification(userData) {
    const adminVerificationModal = document.getElementById(
      "adminVerificationModal"
    );
    const confirmVerificationBtn = document.getElementById(
      "confirmVerificationBtn"
    );
    const cancelVerificationBtn = document.getElementById(
      "cancelVerificationBtn"
    );

    // 사이드바의 '봉사 등록' 링크를 선택합니다.
    const registerVolunteerLink = document.querySelector(
      'a[href="/register-volunteer"]'
    );

    /* // 관리자 인증 여부 확인 및 모달 표시 로직 제거
    if (registerVolunteerLink && adminVerificationModal) {
      // 링크와 모달이 모두 존재하면
      registerVolunteerLink.addEventListener("click", (e) => {
        // currentUser 변수를 사용하여 최신 사용자 정보 확인
        if (currentUser && !currentUser.is_admin) {
          e.preventDefault(); // 관리자가 아니면 기본 링크 이동 방지
          adminVerificationModal.style.display = "block"; // 모달 표시
        } else if (!currentUser) {
          // 아직 사용자 정보 로드 전이라면 일단 이동 시도 (서버에서 막을 것)
          console.warn("User info not loaded yet, proceeding with navigation.");
        }
        // 관리자(currentUser.is_admin === true)인 경우, preventDefault가 호출되지 않아 기본 동작(링크 이동) 수행
      });
    }
    */

    // 모달 내 '예' 버튼 클릭 시 (이 로직은 더 이상 필요 없을 수 있으나, 만약을 위해 남겨둡니다)
    if (confirmVerificationBtn) {
      confirmVerificationBtn.addEventListener("click", () => {
        window.location.href = "/admin-verification"; // 관리자 인증 페이지로 이동
      });
    }

    // 모달 내 '아니오' 버튼 클릭 시 (이 로직은 더 이상 필요 없을 수 있으나, 만약을 위해 남겨둡니다)
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
        `${API_BASE_URL}/api/volunteers?sort=activity_period_start&order=asc`
      );
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
    console.log("Creating card for volunteer:", volunteer);

    // Conditionally create the image tag HTML string
    let imageTagHtml = "";
    if (volunteer.image_path) {
      // Use image_path. Assuming uploads are served from /uploads/
      const imagePath = `/uploads/${volunteer.image_path}`;
      imageTagHtml = `<img src="${imagePath}" alt="${
        volunteer.activity_title || "Volunteer Activity Image"
      }" class="volunteer-image">`;
    }
    // Removed the fallback to default_volunteer.jpg

    const recruitmentStatus =
      volunteer.current_volunteers >= volunteer.max_volunteers
        ? "모집 완료"
        : "모집 중";
    const statusClass =
      volunteer.current_volunteers >= volunteer.max_volunteers
        ? "status-completed"
        : "status-recruiting";

    const card = document.createElement("div");
    card.className = "volunteer-card";

    // Use template literal for cleaner HTML structure
    // Include the imageTagHtml only if it's not empty
    card.innerHTML = `
        ${imageTagHtml} 
        <div class="card-content">
            <h3>${volunteer.activity_title || "제목 없음"}</h3>
            <p><strong>기간:</strong> ${
              volunteer.activity_period_start || "미정"
            } ~ ${volunteer.activity_period_end || "미정"}</p>
            <p><strong>시간:</strong> ${
              volunteer.activity_time_start || "미정"
            } ~ ${volunteer.activity_time_end || "미정"} (${
      volunteer.activity_days || "요일 미정"
    })</p>
            <p><strong>장소:</strong> ${volunteer.address || "주소 미정"}, ${
      volunteer.address_detail || "상세 주소 미정"
    }</p>
            
            <p><strong>내용:</strong> ${
              (volunteer.volunteer_content || "내용 없음").substring(0, 100) +
              ((volunteer.volunteer_content || "").length > 100 ? "..." : "")
            }</p>
            <p><strong>모집 현황:</strong> <span class="${statusClass}">${recruitmentStatus}</span> (${
      volunteer.current_volunteers || 0
    } / ${volunteer.max_volunteers || "제한 없음"} 명)</p>
            <p><strong>인정 시간:</strong> ${
              volunteer.credited_hours || 0
            }시간</p>
            <p><strong>담당자:</strong> ${
              volunteer.manager_name || "정보 없음"
            }</p>
            <p><strong>담당자 이메일:</strong> ${
              volunteer.manager_email || "정보 없음"
            }</p>
            <div class="card-actions">
                <button class="edit-button" data-volunteer-id="${
                  volunteer.id
                }">수정</button>
                <button class="delete-button" data-volunteer-id="${
                  volunteer.id
                }">삭제</button>
            </div>
        </div>
    `;

    // 수정 버튼 이벤트 리스너 추가
    const editBtn = card.querySelector(".edit-button");
    if (editBtn) {
      editBtn.addEventListener("click", (e) => {
        const volunteerId = e.target.getAttribute("data-volunteer-id");
        // 수정 페이지로 이동하는 로직 구현
        console.log(`Edit button clicked for volunteer ID: ${volunteerId}`);
        window.location.href = `/edit-volunteer/${volunteerId}`; // 실제 페이지 이동
      });
    }

    // 삭제 버튼 이벤트 리스너 추가
    const deleteBtn = card.querySelector(".delete-button");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", async (e) => {
        const volunteerId = e.target.getAttribute("data-volunteer-id");
        if (
          confirm(
            `'${volunteer.activity_title}' 봉사활동을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`
          )
        ) {
          // 삭제 API 호출 로직 구현
          console.log(`Delete button clicked for volunteer ID: ${volunteerId}`);

          try {
            // API 엔드포인트 URL 수정 및 DELETE 메소드 사용
            const deleteResponse = await fetch(
              `${API_BASE_URL}/api/volunteer/delete/${volunteerId}`,
              {
                method: "DELETE",
                headers: {
                  // 필요한 경우 인증 헤더 추가 (예: JWT 토큰)
                  // 'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
              }
            );
            const deleteData = await deleteResponse.json();
            if (deleteResponse.ok && deleteData.success) {
              // 응답 상태 코드(ok)와 success 필드 모두 확인
              alert("봉사활동이 삭제되었습니다.");
              card.remove(); // 카드 UI에서 제거
            } else {
              alert(deleteData.message || "삭제에 실패했습니다.");
            }
          } catch (deleteError) {
            console.error("삭제 중 오류:", deleteError);
            alert("삭제 중 오류가 발생했습니다.");
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
