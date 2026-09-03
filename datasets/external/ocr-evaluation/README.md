# OCR 公开测试包

这组文件用于手工对比 OCRWorkbench 的“通用 OCR”和“专业 OCR”。它们不进入
`datasets/manifest.json` 的自动回归集，也不适合用来计算一个综合准确率。
二进制文件只保存在本机，不纳入 Git；在项目根目录运行下面的命令可下载或校验它们：

```bash
python tools/download_public_ocr_dataset.py
```

## 建议测试顺序

1. `04-french-diacritics.pdf` - 干净、简单，先确认重音符号和分行。
2. `05-typewriter-text.png` - 测试打字机字体、噪点和荷兰语。
3. `08-irs-w9-form.pdf` - 测试复杂表单、表格、多栏和六页渲染。
4. `01-hard-illustrated-scan.pdf` - 测试旧书扫描、插图干扰和不规则字体。
5. `02-rotated-skewed-two-column.pdf` - 测试旋转、倾斜校正和双栏阅读顺序。
6. `03-multipage-mixed-scan.pdf` - 测试六页混合扫描、页面续接和长文档稳定性。
7. `06-multilingual-color-map.jpg` - 测试地图文字、彩色线条干扰和多语名称。
8. `07-vector-text-no-font-map.pdf` - 测试没有可用字体映射时的视觉文字识别。

每个文件都小于网页的 20 MB 限制。建议记录：页面是否正确渲染、文字漏识别/错识别、阅读顺序、
页码和坐标证据是否对应，以及通用/专业结果的差异。

## 来源和许可

`01`–`07` 来自 [OCRmyPDF 测试资源](https://github.com/ocrmypdf/OCRmyPDF/tree/main/tests/resources)，
文件未做内容修改，仅为便于测试而重命名。详细归属以上游
[`REUSE.toml`](https://github.com/ocrmypdf/OCRmyPDF/blob/main/REUSE.toml) 为准。
各文件依对应许可使用，不受 OCRWorkbench 仓库 MIT 许可覆盖。

| 文件 | 上游文件 | 许可/属性 |
| --- | --- | --- |
| `01-hard-illustrated-scan.pdf` | `c03-29.pdf` | Public domain |
| `02-rotated-skewed-two-column.pdf` | `rotated_skew.pdf` | (C) 1985 Forat Electronics; GFDL-1.2-or-later or CC-BY-SA-3.0 |
| `03-multipage-mixed-scan.pdf` | `multipage.pdf` | Public domain（按上游 REUSE 标注） |
| `04-french-diacritics.pdf` | `francais.pdf` | (C) 2025 James R. Barlow; CC-BY-SA-4.0 |
| `05-typewriter-text.png` | `typewriter.png` | (C) 2005 Ellywa; GFDL-1.2-or-later or CC-BY-SA-1.0/2.0/2.5/3.0 |
| `06-multilingual-color-map.jpg` | `baiona_color.jpg` | (C) 2014 Euskaldunaa; CC-BY-SA-4.0 |
| `07-vector-text-no-font-map.pdf` | `vector.pdf` | (C) 2018 Catscratch; MIT |
| `08-irs-w9-form.pdf` | [IRS Form W-9](https://www.irs.gov/pub/irs-pdf/fw9.pdf) | U.S. Internal Revenue Service official form |

## SHA-256

```text
C2FF83AF7D028C95209CC7EEBDF80FD5BB4CD292973ED6601E4BAB7D1929F201  01-hard-illustrated-scan.pdf
5122C07D05A61219EB9F8305776EF16DEF6B34C29358E05C5AE2E884A351438F  02-rotated-skewed-two-column.pdf
07987C44650938FA8DCF08C0937691712FDD800669B4607C2C7E3FEE21CB1F80  03-multipage-mixed-scan.pdf
600C27F8DD2EF085A94D3500F6CCDB3B37F4B89AA8FFDF9A00A06A1367887E8B  04-french-diacritics.pdf
6F7A83685A83AF954E9672B3E2DB3253AF165513D2826D780A48E175742F4469  05-typewriter-text.png
CA10778DA7DA3084DE6FECCECA3778836B87CE7CBE814D6837285DF2C12129D7  06-multilingual-color-map.jpg
F530547F86CA3884EF8E2E3CDE686CA04C3A587B09D529A9D74817E77192CBB7  07-vector-text-no-font-map.pdf
2D420CBB4123DCF1FB82595B2359CFBB5D81F00B9DF9D359FCC7AF361D093F53  08-irs-w9-form.pdf
```
