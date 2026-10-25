entry = chr(10) + "### [DeepSeek] " + chr(9226) + " 22/10 08:20 " + chr(8212) + " **KET QUA DESKTOP-BENCH DA VE (2 acc): agent DA CHOI DUOC APP THAT — T26_clipboard 19/20 = 95%!**" + chr(10) + chr(10)
entry += "**A (acc A, 4 task, 80 ep):** ep=80 · win=0 · parse=0.72 · mean_score=0.35 · **stuck=0.75**" + chr(10)
entry += "**B (acc B, 6 task, 120 ep):** ep=120 · **win=25 (20.8%)** · parse=0.91 · mean_score=-0.125 · **stuck=0.625**" + chr(10) + chr(10)
entry += "**| task | win | nhan xet |" + chr(10) + "|---|---|---|" + chr(10)
entry += "| **T26_clipboard** | **19/20 (95%)** | ✅ **agent doc man hinh + bam Ctrl+C/V that — computer-use THAT da chay!** |" + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
