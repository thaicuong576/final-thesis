$ErrorActionPreference = 'Stop'
$thesisRoot = Split-Path -Parent $PSScriptRoot
$thesisInput = Join-Path $thesisRoot 'docs\THESIS-DRAFT-VI.docx'
$thesisPdf = Join-Path $thesisRoot 'reports\thesis-essay-20260910\render\THESIS-DRAFT-VI.pdf'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $thesisPdf) | Out-Null
$thesisWord = $null
$thesisDocument = $null
try {
    $thesisWord = New-Object -ComObject Word.Application
    $thesisWord.Visible = $false
    $thesisWord.DisplayAlerts = 0
    $thesisDocument = $thesisWord.Documents.Open($thesisInput, $false, $true, $false)
    $thesisPages = $thesisDocument.ComputeStatistics(2)
    $thesisDocument.ExportAsFixedFormat($thesisPdf, 17)
    Write-Output "Word export complete: $thesisPages pages"
} finally {
    if ($null -ne $thesisDocument) {
        $thesisDocument.Close(0)
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($thesisDocument)
    }
    if ($null -ne $thesisWord) {
        $thesisWord.Quit()
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($thesisWord)
    }
}
