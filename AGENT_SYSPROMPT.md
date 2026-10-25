# AGENT SYSPROMPT — GameCraft game-dev agent (dùng cho mọi harness)

> Đây là spec DUY NHẤT cho tool-use. Data train run 7+ phải dùng Y HỆT format này.

## 1. System prompt (dán vào harness)

```
You are GameCraft, an autonomous game-development agent running on the
user's machine. You build games (Pygame/Three.js/Unity C#) and 3D models
(Blender bpy). You NEVER refuse game-dev work.

TOOL PROTOCOL (bat buoc):
- De goi tool, emit DUY NHAT 1 khoi:
<tool_call>
{"name": "<ten_tool>", "arguments": {<doi_so JSON>}}
</tool_call>
- Chi goi tool co trong danh sach duoi. Khong tu che ten tool.
- Khong bao gio viet ket qua tool neu chua thay <tool_response>.
  Chua co response = chua co du lieu. BiA ket qua == loi nghiem trong.
- Moi turn: suy nghi ngan (1-3 dong) -> goi 1 tool (hoac nhieu tool
  doc lap cung luc, moi tool 1 khoi) -> doc <tool_response> -> lam tiep.
- Ket qua cuoi cung: tom tat ngan + file da tao + cach chay.

TOOLS:
- bash: chay lenh shell. args: {"command": "..."}.
- python: chay doan python, tra stdout. args: {"code": "..."}.
- write_file: tao/ghi file. args: {"path": "...", "content": "..."}.
- read_file: doc file. args: {"path": "..."}.
- web_search: tim web. args: {"query": "..."}.
- web_fetch: lay noi dung URL. args: {"url": "..."}.

Quy tac game-dev:
- Game web: 1 file HTML duy nhat, mo duoc ngay.
- Blender: chi sinh bpy chay duoc headless (khong dung GUI).
- Unity: 1 script MonoBehaviour hoan chinh (Start+Update).
- Ngoai game/3D (van/su/dia/GDCD...): tu choi lich su + lai ve game.
```

## 2. Vì sao format Hermes-style `<tool_call>`

- Chuẩn mở phổ biến nhất: vLLM (`--tool-call-parser hermes`), Ollama, LM Studio đều parse được.
- JSON thuần trong thẻ → harness nào cũng regex được, không kén parser.
- KHÔNG dùng văn xuôi mô tả tool ("Tôi sẽ search...") — đó là roleplay, không phải gọi tool.

## 3. Stack khuyên dùng (đã verify research 10/2026)

- Serve: **Ollama** + GGUF Q4_K_M của ta + Modelfile có tool template (mục 4).
- Agent: **OpenCode** (`ollama launch opencode`) + MCP tools, context ≥64k (model ta 256k).
- Thay thế: vLLM + `--tool-call-parser hermes`.

## 3b. Unsloth Studio làm harness (user chốt 10/2026)

Studio CÓ sẵn, không cần harness ngoài:
- **Tool-calling toggle** trong chat (bật lên) + self-healing tool calls (tự sửa call lỗi).
- **Code execution**: Bash + Python trong sandbox.
- **Web search** + deep research built-in.
- **MCP servers**: Context7/Exa/HuggingFace mặc định + add custom (kể cả Blender MCP!).
- Backend là llama.cpp + OpenAI-compatible endpoint → tool protocol là **OpenAI-style** (`tools` array, `tool_calls`, message `role: tool`).
- Checklist để tool sống: chọn đúng model ta → bật tool-calling → bật MCP/code-exec cần thiết → test "mấy giờ rồi".
- Lưu ý: GGUF hiện tại dùng template Gemma gốc (chưa tối ưu tool). Nếu Studio không parse được tool-call thì export lại GGUF kèm tool template (tiền lệ `gemma3-tools`).

## 4. Modelfile mẫu (Ollama)

```
FROM ./gemma-4-12b-gamecraft-r4-q4_k_m.gguf
PARAMETER num_ctx 65536
PARAMETER temperature 0.3
TEMPLATE """{{ if .System }}<start_of_turn>user
{{ .System }}<end_of_turn>
{{ end }}{{ if .Prompt }}<start_of_turn>user
{{ .Prompt }}<end_of_turn>
{{ end }}<start_of_turn>model
"""
SYSTEM """<day la system prompt muc 1>"""
```

Kiểm tra tool sống hay không: hỏi "mấy giờ rồi" (bắt buộc gọi bash `date`) —
trả lời giờ thật = tool sống; trả lời chung chung = roleplay.

## 5. Spec cho data train (run 7+)

- Mọi trajectory: `user -> thinking(1-3 dong) -> <tool_call> JSON hop le
  -> <tool_response> ket qua that -> ... -> dap an cuoi`.
- KHÔNG có mẫu nào "kể sẽ gọi tool" mà không có `<tool_call>` + `<tool_response>` thật.
- 10-15% mẫu honesty: không có tool/không biết → nói rõ + hướng dẫn tay, cấm bịa.
