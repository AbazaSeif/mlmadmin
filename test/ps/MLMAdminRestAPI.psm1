function Send-MLMAdminRequest {
    [CmdletBinding()]
    param(
    [Parameter(Position=0, Mandatory=$true)] [string]$Uri,
    [Parameter(Position=1, Mandatory=$false)] [object]$Token,
    [Parameter(Position=2, Mandatory=$false)] [object]$Data
    )
    $method = 'GET'

    if ($Data) {
        $method = 'POST'

        try {
            $jsonData = ConvertTo-Json -InputObject $Data
        } catch { throw $_ }

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonData)
    }
    $webRequest = [System.Net.WebRequest]::Create($Uri)
    $webRequest.Accept = 'application/json'
    $webRequest.ContentType = 'application/json'
    $webRequest.Method = $method

    # add the token to the headers
    if ($Token) {
        $webRequest.Headers.Add('Authorization', 'Token {0}' -f $Token)
    }

    if ($Data) {
        # post data
        $webRequest.ContentLength = $bytes.Length
        $requestStream = [System.IO.Stream]$webRequest.GetRequestStream()
        $requestStream.Write($bytes, 0, $bytes.Length)
        $requestStream.Close()
    }
    try {
        # read response
        [System.Net.HttpWebResponse]$webResponse = $webRequest.GetResponse()
        $streamReader = New-Object System.IO.StreamReader($webResponse.GetResponseStream())
        $result = $streamReader.ReadToEnd()
    } catch { throw $_ }

    return ConvertFrom-Json -InputObject $result
}


function Get-MLMAdminToken {
    [CmdletBinding()]
    param(
    [Parameter(Position=0, Mandatory=$true)] [string]$Uri,
    [Parameter(Position=1, Mandatory=$true)] [object]$Data
    )
    return (Send-MLMAdminRequest -Uri $Uri -Data $Data).token
}


Export-ModuleMember -Function Get-MLMAdminToken, Send-MLMAdminRequest