const express = require("express");
const nodemailer = require("nodemailer");
const cors = require("cors");
require("dotenv").config();

const app = express();

// CORS 설정
app.use(cors());
app.use(express.json());

// 정적 파일 제공
app.use(express.static(__dirname));

// 라우트 설정
app.get("/", (req, res) => {
  res.sendFile(__dirname + "/login.html");
});

app.get("/main", (req, res) => {
  res.sendFile(__dirname + "/main.html");
});

app.get("/signup", (req, res) => {
  res.sendFile(__dirname + "/signup.html");
});

// 이메일 전송을 위한 설정
const transporter = nodemailer.createTransport({
  service: "Gmail",
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
  },
});

// 인증 코드 저장을 위한 임시 저장소
const verificationCodes = new Map();

// 이메일 인증 코드 전송 엔드포인트
app.post("/send-verification", async (req, res) => {
  try {
    const { email } = req.body;

    // 6자리 인증 코드 생성
    const verificationCode = Math.floor(
      100000 + Math.random() * 900000
    ).toString();

    // 이메일 전송
    await transporter.sendMail({
      from: process.env.EMAIL_USER,
      to: email,
      subject: "회원가입 인증 코드",
      text: `회원가입 인증 코드: ${verificationCode}\n\n이 코드는 10분간 유효합니다. 이메일 인증번호를 작성해 주세요`,
    });

    // 인증 코드 저장 (10분 후 만료)
    verificationCodes.set(email, {
      code: verificationCode,
      expires: Date.now() + 600000, // 10분
    });

    // 10분 후 자동 삭제
    setTimeout(() => {
      verificationCodes.delete(email);
    }, 600000);

    res.json({ success: true, message: "인증 코드가 전송되었습니다." });
  } catch (error) {
    console.error("이메일 전송 오류:", error);
    res
      .status(500)
      .json({ success: false, message: "이메일 전송에 실패했습니다." });
  }
});

// 인증 코드 확인 엔드포인트
app.post("/verify-code", (req, res) => {
  const { email, code } = req.body;

  const verification = verificationCodes.get(email);

  if (!verification) {
    return res.json({ success: false, message: "인증 코드가 만료되었습니다." });
  }

  if (verification.expires < Date.now()) {
    verificationCodes.delete(email);
    return res.json({ success: false, message: "인증 코드가 만료되었습니다." });
  }

  if (verification.code !== code) {
    return res.json({ success: false, message: "잘못된 인증 코드입니다." });
  }

  verificationCodes.delete(email);
  res.json({ success: true, message: "인증이 완료되었습니다." });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다.`);
});
