param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("files","folder")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()

$owner = New-Object System.Windows.Forms.Form
$owner.Text = "MediaHub Smart Renamer"
$owner.Width = 1
$owner.Height = 1
$owner.ShowInTaskbar = $false
$owner.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedToolWindow
$owner.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$owner.TopMost = $true
$owner.Opacity = 0
$owner.Show()
$owner.Activate()

try {
    if ($Mode -eq "files") {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = "Dateien auswählen"
        $dialog.Multiselect = $true
        $dialog.CheckFileExists = $true
        $dialog.CheckPathExists = $true
        $dialog.RestoreDirectory = $true

        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            [Console]::Out.Write(($dialog.FileNames | ConvertTo-Json -Compress))
        } else {
            [Console]::Out.Write("[]")
        }
    } else {
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = "Ordner auswählen"
        $dialog.ShowNewFolderButton = $false

        if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {
            [Console]::Out.Write((@($dialog.SelectedPath) | ConvertTo-Json -Compress))
        } else {
            [Console]::Out.Write("[]")
        }
    }
}
finally {
    $owner.Close()
    $owner.Dispose()
}
