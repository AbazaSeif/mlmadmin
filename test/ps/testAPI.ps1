Import-Module ('C:\Scripts\Modules\MLMAdminRestAPI.psm1')

$dataAuth = @{
    'username' = 'admin'
    'password' = 'password'
}

$MLMAdmin = 'https://mlmadmin.domain.corp:6443'

$Uri = @{
    'token' = $MLMAdmin + '/api-token-auth/'
    'mlm'   = $MLMAdmin + '/api/mlm/'
}

# get token
$Token = Get-MLMAdminToken -Uri $Uri['token'] -Data $dataAuth

# get data
$Mlm = Send-MLMAdminRequest -Uri $Uri['mlm'] -Token $Token

$dataMLM = @{
    'mlm' = 'mlm-test'
    'address' = @('neo_matrix@example.com', 'agent_smith@example.com', 'white_rabbit@example.com')
}

# post recipients
Send-MlmadminRequest -Uri $Uri['mlm'] -Token $Token -Data $dataMLM