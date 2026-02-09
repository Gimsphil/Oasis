$tempDir = $env:TEMP
$scriptPath = Join-Path $tempDir "_db_query5.py"
$resultPath = Join-Path $tempDir "_db_result5.txt"

$scriptContent = @"
import os

result_lines = []

# Decode hex values to understand the data
hex_pairs = {
    "col[0] ID": "4944",
    "col[1]": "ed9288ebaa85",
    "col[2]": "eab79ceab2a9",
    "col[3]": "eb8ba8ec9c84",
    "col[4]": "ebacbceab080eca095ebb3b4",
    "col[5]": "eb8ba8eab0803150",
    "col[6]": "eb8ba8eab080ec9e90eba38c",
    "col[7]": "eb8ba8eab0803250",
    "col[8]": "eab080eab2a9eca1b0ec82ac",
    "col[9]": "eb8ba8eab0803350",
    "col[10]": "eab1b0eb9e98eab080eab2a9",
    "col[11]": "eb8ba8eab0803450",
    "col[12]": "eb8ba8eab0803528eca1b0ec82ac29",
    "col[13]": "eb8ba8eab0803550",
    "col[14]": "eb8ba8eab0803628eca1b0ec82ac29",
    "col[15]": "eb8ba8eab0803650",
    "col[28]": "ec95bdeca084eba5a0",
    "col[29]": "eab3b5eb8f99eca3bced839d",
    "col[30]": "eb85b8ed95a0",
    "col[31]": "ec9eaced95a0",
    "col[37]": "ebaaa9eba19d31",
    "col[38]": "ebaaa9eba19d32",
    "col[39]": "ebaaa9eba19d33",
    "col[43]": "ec95bdecb9ad",
    "col[45]": "ec82b0ecb69cebaaa9eba19d",
    "col[46]": "eab280ec8389ebaaa9eba19d",
    "col[47]": "ec82b0ecb69cec8898ec8b9d",
}

for key, hexval in hex_pairs.items():
    decoded = bytes.fromhex(hexval).decode('utf-8')
    result_lines.append(key + " = " + decoded)

result_lines.append("")
result_lines.append("=== 강제전선관 data decoded ===")
# Decode the actual data hex
data_hex = {
    "col1 (품명)": "eab095eca09ceca084ec84a0eab480",
    "col2 (규격)": "ec9584ec97b0eb8f84203136e38e9c",
    "col45 (산출목록)": None,
}
for key, hexval in data_hex.items():
    if hexval:
        decoded = bytes.fromhex(hexval).decode('utf-8')
        result_lines.append(key + " = " + decoded)

# Also decode the col45 산출목록 value for 강제전선관
# From earlier: col45 = '강제전선관 아연도 16 mm' (approximately)
# Let me re-verify by decoding what we saw
result_lines.append("")
result_lines.append("col45 산출목록 contained: 강제전선관 아연도 16 mm")
result_lines.append("col2 규격 contained: 아연도 16㎜")
result_lines.append("")
result_lines.append("If code does: output_name = f'{item_name} {spec_name}'")
result_lines.append("Where item_name = col45 (산출목록) = '강제전선관 아연도 16 mm'")
result_lines.append("And spec_name = col2 (규격) = '아연도 16㎜'")
result_lines.append("Result = '강제전선관 아연도 16 mm 아연도 16㎜'  <-- DUPLICATE!")

output_path = os.path.join(os.environ["TEMP"], "_db_result5.txt")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(chr(10).join(result_lines))
    f.flush()
    os.fsync(f.fileno())
"@

[System.IO.File]::WriteAllText($scriptPath, $scriptContent, [System.Text.UTF8Encoding]::new($false))
cmd /c "python `"$scriptPath`""
Start-Sleep -Seconds 3

if (Test-Path $resultPath) {
    [System.IO.File]::ReadAllText($resultPath, [System.Text.UTF8Encoding]::new($false))
} else {
    Write-Output "No result"
}
