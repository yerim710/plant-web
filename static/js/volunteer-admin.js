// 봉사 공고 목록 조회
async function fetchVolunteerPosts() {
  try {
    const response = await fetch("/admin/volunteer/list", {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include", // 세션 쿠키 포함
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        error.message || "봉사 공고 목록을 불러오는데 실패했습니다."
      );
    }

    const data = await response.json();
    return data.posts;
  } catch (error) {
    console.error("Error:", error);
    alert(error.message);
    return [];
  }
}

// 봉사 공고 등록
async function createVolunteerPost(postData) {
  try {
    // 날짜 형식 변환 (YYYY-MM-DD)
    const formattedData = {
      ...postData,
      date: new Date(postData.date).toISOString().split("T")[0],
    };

    const response = await fetch("/admin/volunteer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify(formattedData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || "봉사 공고 등록에 실패했습니다.");
    }

    const data = await response.json();
    alert(data.message);
    return true;
  } catch (error) {
    console.error("Error:", error);
    alert(error.message);
    return false;
  }
}

// 봉사 공고 수정
async function updateVolunteerPost(postId, postData) {
  try {
    // 날짜 형식 변환 (YYYY-MM-DD)
    const formattedData = {
      ...postData,
      date: new Date(postData.date).toISOString().split("T")[0],
    };

    const response = await fetch(`/admin/volunteer/${postId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify(formattedData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || "봉사 공고 수정에 실패했습니다.");
    }

    const data = await response.json();
    alert(data.message);
    return true;
  } catch (error) {
    console.error("Error:", error);
    alert(error.message);
    return false;
  }
}

// 봉사 공고 삭제
async function deleteVolunteerPost(postId) {
  if (!confirm("정말로 이 봉사 공고를 삭제하시겠습니까?")) {
    return false;
  }

  try {
    const response = await fetch(`/admin/volunteer/${postId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || "봉사 공고 삭제에 실패했습니다.");
    }

    const data = await response.json();
    alert(data.message);
    return true;
  } catch (error) {
    console.error("Error:", error);
    alert(error.message);
    return false;
  }
}

// 봉사 공고 목록 렌더링
function renderVolunteerPosts(posts) {
  const container = document.getElementById("volunteerPostsContainer");
  if (!container) return;

  container.innerHTML = posts
    .map(
      (post) => `
        <div class="volunteer-post" data-id="${post.id}">
            <h3>${post.title}</h3>
            <p>${post.description}</p>
            <p>위치: ${post.location || "미지정"}</p>
            <p>날짜: ${new Date(post.date).toLocaleDateString()}</p>
            <div class="post-actions">
                <button onclick="editPost(${post.id})">수정</button>
                <button onclick="deletePost(${post.id})">삭제</button>
            </div>
        </div>
    `
    )
    .join("");
}

// 봉사 공고 수정 폼 표시
function showEditForm(post) {
  const form = document.getElementById("editForm");
  if (!form) return;

  form.style.display = "block";
  form.dataset.postId = post.id;

  document.getElementById("editTitle").value = post.title;
  document.getElementById("editDescription").value = post.description;
  document.getElementById("editLocation").value = post.location || "";
  document.getElementById("editDate").value = post.date;
}

// 봉사 공고 등록 폼 제출
async function handleCreateSubmit(event) {
  event.preventDefault();

  const postData = {
    title: document.getElementById("title").value,
    description: document.getElementById("description").value,
    location: document.getElementById("location").value,
    date: document.getElementById("date").value,
  };

  const success = await createVolunteerPost(postData);
  if (success) {
    event.target.reset();
    const posts = await fetchVolunteerPosts();
    renderVolunteerPosts(posts);
  }
}

// 봉사 공고 수정 폼 제출
async function handleEditSubmit(event) {
  event.preventDefault();

  const postId = event.target.dataset.postId;
  const postData = {
    title: document.getElementById("editTitle").value,
    description: document.getElementById("editDescription").value,
    location: document.getElementById("editLocation").value,
    date: document.getElementById("editDate").value,
  };

  const success = await updateVolunteerPost(postId, postData);
  if (success) {
    event.target.style.display = "none";
    const posts = await fetchVolunteerPosts();
    renderVolunteerPosts(posts);
  }
}

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", async () => {
  // 봉사 공고 목록 로드
  const posts = await fetchVolunteerPosts();
  renderVolunteerPosts(posts);

  // 폼 이벤트 리스너 등록
  const createForm = document.getElementById("createForm");
  if (createForm) {
    createForm.addEventListener("submit", handleCreateSubmit);
  }

  const editForm = document.getElementById("editForm");
  if (editForm) {
    editForm.addEventListener("submit", handleEditSubmit);
  }
});
