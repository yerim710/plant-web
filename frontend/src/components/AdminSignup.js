import React, { useState } from "react";
import axios from "axios";
import "./AdminSignup.css";

const AdminSignup = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [emailCheck, setEmailCheck] = useState(false);
  const [emailMessage, setEmailMessage] = useState("");
  const [passwordMatch, setPasswordMatch] = useState(true);
  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (name === "confirmPassword") {
      setPasswordMatch(value === formData.password);
    }
  };

  const checkEmail = async () => {
    try {
      const response = await axios.post(
        "http://localhost:8080/api/check-email",
        {
          email: formData.email,
        }
      );
      setEmailCheck(response.data.available);
      setEmailMessage(
        response.data.available
          ? "사용 가능한 이메일입니다."
          : "이미 사용 중인 이메일입니다."
      );
    } catch (error) {
      setEmailMessage("이메일 확인 중 오류가 발생했습니다.");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!emailCheck) {
      setMessage("이메일 중복 확인을 해주세요.");
      return;
    }

    if (!passwordMatch) {
      setMessage("비밀번호가 일치하지 않습니다.");
      return;
    }

    try {
      const response = await axios.post(
        "http://localhost:8080/api/admin/signup",
        formData
      );
      setMessage("회원가입이 완료되었습니다!");
      // 성공 시 로그인 페이지로 리다이렉트
      setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
    } catch (error) {
      setMessage("회원가입 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="signup-container">
      <h2>관리자 회원가입</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>이름</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label>이메일</label>
          <div className="email-input-group">
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
            />
            <button type="button" onClick={checkEmail}>
              중복확인
            </button>
          </div>
          <p className={emailCheck ? "success" : "error"}>{emailMessage}</p>
        </div>

        <div className="form-group">
          <label>비밀번호</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-group">
          <label>비밀번호 확인</label>
          <input
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
          />
          {!passwordMatch && (
            <p className="error">비밀번호가 일치하지 않습니다.</p>
          )}
        </div>

        <button type="submit" className="submit-btn">
          회원가입
        </button>
      </form>
      {message && (
        <p className={message.includes("완료") ? "success" : "error"}>
          {message}
        </p>
      )}
    </div>
  );
};

export default AdminSignup;
