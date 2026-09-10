param([switch]$ConnectExisting)
$ErrorActionPreference='Stop'
$thesisRoot=Split-Path -Parent $PSScriptRoot
$thesisInput=Join-Path $thesisRoot 'docs\THESIS-DRAFT-VI.docx'
$thesisPdf=Join-Path $thesisRoot 'reports\thesis-visuals-20260910\render\THESIS-DRAFT-VI.pdf'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $thesisPdf) | Out-Null
if ($ConnectExisting) {
    $thesisWord=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    $thesisDocument=$null
    foreach ($thesisCandidate in $thesisWord.Documents) {
        if ($thesisCandidate.FullName -eq $thesisInput) {$thesisDocument=$thesisCandidate}
    }
    if ($null -eq $thesisDocument) {throw 'Exact thesis document not open'}
} else {
    $thesisWord=New-Object -ComObject Word.Application
    $thesisWord.Visible=$false
    $thesisWord.DisplayAlerts=0
    Write-Output 'Created hidden Word instance'
    $thesisDocument=$thesisWord.Documents.OpenNoRepairDialog($thesisInput,$false,$true,$false)
    Write-Output 'Opened thesis document'
}
$thesisDocument.ExportAsFixedFormat([string]$thesisPdf,17)
Write-Output ('Exported PDF, pages: '+$thesisDocument.ComputeStatistics(2))
$thesisDocument.Close(0)
if ($thesisWord.Visible -eq $false -and $thesisWord.Documents.Count -eq 0) {$thesisWord.Quit()}
[void][Runtime.InteropServices.Marshal]::ReleaseComObject($thesisDocument)
[void][Runtime.InteropServices.Marshal]::ReleaseComObject($thesisWord)
