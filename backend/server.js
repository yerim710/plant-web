const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const bcrypt = require("bcryptjs");

const app = express();

// 미들웨어 설정
app.use(cors());
app.use(express.json());

// MongoDB 연결
mongoose.connect("mongodb://localhost:27017/admin_db", {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});

// 관리자 스키마 정의
const adminSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
});

const Admin = mongoose.model("Admin", adminSchema);

// 이메일 중복 확인 API
app.post("/api/check-email", async (req, res) => {
  try {
    const { email } = req.body;
    const existingAdmin = await Admin.findOne({ email });
    res.json({ available: !existingAdmin });
  } catch (error) {
    res.status(500).json({ error: "서버 오류가 발생했습니다." });
  }
});

// 회원가입 API
app.post("/api/admin/signup", async (req, res) => {
  try {
    const { name, email, password } = req.body;

    // 이메일 중복 확인
    const existingAdmin = await Admin.findOne({ email });
    if (existingAdmin) {
      return res.status(400).json({ error: "이미 사용 중인 이메일입니다." });
    }

    // 비밀번호 해시화
    const hashedPassword = await bcrypt.hash(password, 10);

    // 새 관리자 생성
    const admin = new Admin({
      name,
      email,
      password: hashedPassword,
    });

    await admin.save();
    res.status(201).json({ message: "회원가입이 완료되었습니다." });
  } catch (error) {
    res.status(500).json({ error: "서버 오류가 발생했습니다." });
  }
});

const PORT = 8080;
app.listen(PORT, () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다.`);
});
