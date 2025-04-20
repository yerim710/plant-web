document.addEventListener("DOMContentLoaded", () => {
  const writePostBtn = document.getElementById("writePostBtn");
  const postModal = document.getElementById("postModal");
  const closePostModal = document.getElementById("closePostModal");
  const postForm = document.getElementById("postForm");
  const postList = document.getElementById("postList");

  // 글쓰기 버튼 클릭 이벤트
  writePostBtn.addEventListener("click", () => {
    postModal.style.display = "block";
  });

  // 모달 닫기 버튼 클릭 이벤트
  closePostModal.addEventListener("click", () => {
    postModal.style.display = "none";
    postForm.reset();
  });

  // 모달 외부 클릭 시 닫기
  window.addEventListener("click", (e) => {
    if (e.target === postModal) {
      postModal.style.display = "none";
      postForm.reset();
    }
  });

  // 게시글 등록 폼 제출 이벤트
  postForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("postTitle").value;
    const content = document.getElementById("postContent").value;
    const imageFile = document.getElementById("postImage").files[0];
    const currentUser = JSON.parse(localStorage.getItem("currentUser"));

    if (!currentUser) {
      alert("로그인이 필요합니다.");
      window.location.href = "login.html";
      return;
    }

    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("content", content);
      formData.append("author", currentUser.email);
      if (imageFile) {
        formData.append("image", imageFile);
      }

      const response = await fetch("http://localhost:5000/api/posts", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        postModal.style.display = "none";
        postForm.reset();
        loadPosts();
      } else {
        alert(data.message || "게시글 등록에 실패했습니다.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("게시글 등록 중 오류가 발생했습니다.");
    }
  });

  // 게시글 목록 로드
  async function loadPosts() {
    try {
      const response = await fetch("http://localhost:5000/api/posts");
      const data = await response.json();

      if (data.success) {
        postList.innerHTML = "";
        data.posts.forEach((post, index) => {
          const row = document.createElement("tr");
          row.innerHTML = `
                        <td>${index + 1}</td>
                        <td><a href="#" class="post-link" data-id="${
                          post.id
                        }">${post.title}</a></td>
                        <td>${post.author}</td>
                        <td>${new Date(
                          post.created_at
                        ).toLocaleDateString()}</td>
                        <td>${post.views}</td>
                    `;
          postList.appendChild(row);
        });

        // 게시글 제목 클릭 이벤트
        document.querySelectorAll(".post-link").forEach((link) => {
          link.addEventListener("click", (e) => {
            e.preventDefault();
            const postId = e.target.dataset.id;
            viewPost(postId);
          });
        });
      }
    } catch (error) {
      console.error("Error:", error);
      alert("게시글 목록을 불러오는 중 오류가 발생했습니다.");
    }
  }

  // 게시글 상세 보기
  async function viewPost(postId) {
    try {
      const response = await fetch(`http://localhost:5000/api/posts/${postId}`);
      const data = await response.json();

      if (data.success) {
        // 게시글 상세 보기 페이지로 이동
        window.location.href = `post.html?id=${postId}`;
      } else {
        alert(data.message || "게시글을 불러오는 중 오류가 발생했습니다.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("게시글을 불러오는 중 오류가 발생했습니다.");
    }
  }

  // 초기 게시글 목록 로드
  loadPosts();
});
