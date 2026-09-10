$ErrorActionPreference='Stop'
$thesisWord=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
foreach ($thesisDoc in $thesisWord.Documents) {
    if ($thesisDoc.FullName -eq 'D:\eddie-projects\personal-projects\final-thesis\docs\THESIS-DRAFT-VI.docx') {
        Write-Output ('Thesis pages: '+$thesisDoc.ComputeStatistics(2))
        Write-Output ('Tables: '+$thesisDoc.Tables.Count+'; images: '+$thesisDoc.InlineShapes.Count)
        $thesisDoc.ExportAsFixedFormat('D:\eddie-projects\personal-projects\final-thesis\reports\thesis-visuals-20260910\render\THESIS-DRAFT-VI.pdf', 17)
        Write-Output 'PDF export completed'
        $thesisDoc.Close(0)
    }
}
if ($thesisWord.Visible -eq $false -and $thesisWord.Documents.Count -eq 0) {$thesisWord.Quit()}
[void][Runtime.InteropServices.Marshal]::ReleaseComObject($thesisWord)
