# ADR-0005: SQLite (+FTS5) ก่อน vector memory

- สถานะ: Accepted
- วันที่: 2026-11-13

## Context

ต้องเก็บ sessions, turns, actions, timers, facts และค้นย้อนหลัง
เครื่องมี RAM จำกัด การเพิ่ม vector DB/embedding model กินทรัพยากรและเพิ่ม latency

## Decision

ใช้ SQLite ไฟล์เดียว (WAL mode) ที่ `~/.local/share/javis/javis.db`
ค้นข้อความด้วย FTS5 (trigram/tokenizer สำหรับไทยเท่าที่ทำได้)
ยังไม่ทำ semantic search; ออกแบบ abstraction `MemoryStore` ให้เปลี่ยนภายหลังได้

## Consequences

ข้อดี
- เบา, ไม่มี service เพิ่ม, backup ง่าย (copy ไฟล์)
- ACID และ query ยืดหยุ่นด้วย SQL
- เพียงพอสำหรับประวัติ 30 วันและ facts จำนวนเล็ก

ข้อเสีย
- FTS5 กับภาษาไทย (ไม่มีช่องว่างระหว่างคำ) คุณภาพจำกัด → ต้องใช้ trigram หรือ pre-tokenize
- ไม่เข้าใจความหมาย (semantic) → ค้นด้วยคำพ้องไม่ได้
- ถ้าข้อมูลโตมากต้องมี vacuum/retention

## Alternatives

- sqlite-vec / Chroma / Qdrant: ดีกว่าเชิง semantic แต่เพิ่ม RAM/model และ complexity
- Postgres: มีอยู่บนเครื่อง (self-agent) แต่เกินความจำเป็นและผูก dependency

## หมายเหตุ

ถ้า M3 พบว่าค้นโน้ตไม่ตรงคำ ถือเป็นสัญญาณให้ประเมิน sqlite-vec + embedding เล็ก
(เช่น bge-small) โดยวัด RAM และ latency ก่อนตัดสินใจ

## ข้อโต้แย้ง / แย้งแผน (Critique)

1. **FTS5 ไร้ประโยชน์กับภาษาไทยหากไม่ทำ Pre-segmentation:** SQLite FTS5 อาศัย space ในการแยกคำ สำหรับภาษาไทยที่เขียนติดกัน FTS5 แบบปกติจะไม่สามารถค้นคำได้เลย การใช้ `trigram tokenizer` ช่วยได้บางส่วนแต่จะทำให้ดัชนีบวม (Index Bloat) และค้นคำสั้นได้ไม่แม่นยำ
2. **ข้อเสนอแนะ:** จำเป็นต้องใช้ `pythainlp.word_tokenize` คั่นด้วย space ก่อนบันทึกลง virtual table หรือยอมรับการใช้ SQL `LIKE '%keyword%'` สำหรับประวัติข้อความสั้น 30 วัน ซึ่งเพียงพอและเร็วกว่าโดยไม่ต้องแบกความยุ่งยากของ FTS5 ภาษาไทยในระยะแรก

✅ **มติการปรับปรุง (ADR-0005 Resolution v0.2):**
- ในระยะแรก ใช้การค้นหาข้อความด้วย SQL `LIKE '%keyword%'` สำหรับประวัติข้อความ 30 วัน ซึ่งรวดเร็ว น้ำหนักเบา และตรงไปตรงมา ไม่ต้องแบกความซับซ้อนของ FTS5 บนภาษาไทย
- หากต้องการทำ Full-Text Search ในอนาคต ให้ใช้ `pythainlp` ทำการ Word Segmentation (ตัดคำคั่นด้วยช่องว่าง) ก่อนบันทึกลง virtual table
