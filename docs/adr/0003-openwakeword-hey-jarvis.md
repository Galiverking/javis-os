# ADR-0003: Wake word "hey jarvis" ด้วย openWakeWord

- สถานะ: Accepted
- วันที่: 2026-11-13

## Context

ผู้ใช้ต้องการเรียกด้วยเสียงโดยไม่กดปุ่ม ตัวเลือกหลัก:
- **openWakeWord** — โอเพนซอร์ส, ONNX, มี pretrained `hey_jarvis`, รันบน CPU ได้
- **Porcupine** — แม่นและเบา แต่ต้องสมัคร access key และมีข้อจำกัดการใช้งานฟรี
- **Vosk keyword spotting** — ต้องโหลด ASR model เล็กและ tune เอง
- **train เอง** — ยืดหยุ่น แต่ใช้เวลาและข้อมูลมาก

## Decision

ใช้ `openwakeword` + pretrained model `hey_jarvis` (threshold ~0.5)
พร้อม hotkey `Ctrl+Alt+J` เป็นทางเลือกสำรองที่เชื่อถือได้เสมอ
ออกแบบให้ `wake` เป็นโมดูลที่ swap ได้ในอนาคต

## Consequences

ข้อดี
- ฟรี ไม่มี account, ทำงาน offline, CPU ต่ำ
- มีเส้นทางอัปเกรดเป็น custom wake word ได้ภายหลัง
- ลดความเสี่ยงด้าน privacy (เสียงไม่ถูกส่งออกเพื่อ wake detection)

ข้อเสีย
- คำว่า "Jarvis" เป็นคำที่โมเดลทั่วไปอาจ trigger ง่ายกว่าคำเฉพาะ
- ประสิทธิภาพจริงขึ้นกับไมโครโฟนและ noise → ต้อง calibrate
- ถ้าต้องการคำไทย/คำเฉพาะ ต้อง train เอง (M4)

## Alternatives

Porcupine (แม่นกว่าแต่มีค่าใช้จ่าย/ข้อผูกมัด), Vosk KWS (เบากว่าแต่ tune ยาก),
push-to-talk only (ไม่ตอบโจทย์ hands-free)

## หมายเหตุ

MVP (M1) ใช้ hotkey ก่อน; wake word เริ่ม M2 หลังวัด false accept/reject จริง

## ข้อโต้แย้ง / แย้งแผน (Critique)

1. **ปัญหาสำเนียงไทยกับโมเดลสำเร็จรูป:** `hey_jarvis` ของ openWakeWord ฝึกจากเสียงสำเนียงภาษาอังกฤษเป็นหลัก เมื่อพูดด้วยน้ำเสียงและวรรณยุกต์ไทยธรรมชาติ ("เฮ้ จาวิส") อัตราการไม่ติด (False Reject) จะสูงมากจนสร้างความหงุดหงิด
2. **False Trigger จากสื่อ/คลิปวิดีโอ:** คำว่า "Jarvis" ปรากฏบ่อยในสื่อทั่วไป หากเปิดดูคลิป YouTube หรือภาพยนตร์ ระบบจะตื่นขึ้นมาเองเรื่อยๆ
3. **ข้อเสนอแนะ:** ควรกำหนดให้การใช้ Wake Word เป็น secondary feature ในระยะแรก และเน้น PTT (Push-to-Talk) ผ่านแป้นคีย์บอร์ดที่เชื่อถือได้ 100% จนกว่าจะสามารถเทรนหรือ fine-tune โมเดลด้วยชุดเสียงภาษาไทยจริงได้

✅ **มติการปรับปรุง (ADR-0003 Resolution v0.2):**
- ปรับลดสถานะของ Wake Word "Hey Jarvis" ให้เป็น **Secondary / Experimental Feature** และปรับเกณฑ์ความแม่นยำให้สมจริงบนสำเนียงไทย
- ยกระดับ **Cinnamon Native Shortcut (`Ctrl+Alt+J`)** ผ่าน `javis ptt` ขึ้นเป็น **Primary Interaction Method** ที่เชื่อถือได้ 100%
- ปิด Wake Word เป็นค่าเริ่มต้นเมื่อใช้ลำโพงในตัวเครื่องเพื่อป้องกันปัญหา False Trigger จากสื่อและ Acoustic Echo
