$ErrorActionPreference = 'Stop'
$thesisWordCheck = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
Write-Output ('Visible: ' + $thesisWordCheck.Visible)
Write-Output ('Documents: ' + $thesisWordCheck.Documents.Count)
foreach ($thesisOpenDoc in $thesisWordCheck.Documents) {
    Write-Output $thesisOpenDoc.FullName
    Write-Output ('Saved: ' + $thesisOpenDoc.Saved)
    Write-Output ('Pages: ' + $thesisOpenDoc.ComputeStatistics(2))
    if ($thesisOpenDoc.FullName -eq 'D:\eddie-projects\personal-projects\final-thesis\docs\THESIS-DRAFT-VI.docx') {
        $thesisOpenDoc.ExportAsFixedFormat('D:\eddie-projects\personal-projects\final-thesis\reports\thesis-essay-20260910\render\THESIS-DRAFT-VI.pdf', 17)
        Write-Output 'PDF exported by connected document'
    }
}
if ($thesisWordCheck.Visible -eq $false -and $thesisWordCheck.Documents.Count -eq 1 -and $thesisWordCheck.Documents.Item(1).FullName -eq 'D:\eddie-projects\personal-projects\final-thesis\docs\THESIS-DRAFT-VI.docx') {
    $thesisWordCheck.Documents.Item(1).Close(0)
    $thesisWordCheck.Quit()
    Write-Output 'Closed only the hidden thesis QA instance'
}
[void][Runtime.InteropServices.Marshal]::ReleaseComObject($thesisWordCheck)
