#!/usr/bin/perl

use v5.10;
use strict;
use warnings;
use JSON;
use REST::Client;
use Data::Dumper; # dev only

# declare all variables
my (
    $client,
    $data,
    $data_arr,
    $data_err1,
    $data_err2,
    $data_hr,
    $django,
    $headers,
    $json_data,
    $mlmadmin,
    $password,
    $response,
    $response_arr,
    $response_err1,
    $response_err2,
    $response_hr,
    $token,
    $urls,
    $username,
);

# declare all subroutines
sub django_get_data;
sub django_post_data;


$mlmadmin = 'https://mlmadmin.example.com:6443';
$urls = {
    token => $mlmadmin . '/api-token-auth/',
    mlm   => $mlmadmin . '/api/mlm/',
};

$username = 'admin';
$password = 'password';

$headers = {
    Accept       => 'application/json',
    Content_Type => 'application/json',
};

$data = {
    username => $username,
    password => $password,
};

$json_data = encode_json($data);


# create a connection object
$client = REST::Client->new();

# get the token
$client->POST($urls->{'token'}, $json_data, $headers);

$response = decode_json($client->responseContent());
$token = $response->{'token'};

# add the token to the headers
$client->addHeader('Authorization' => "Token $token");

# get MLMs
$response = django_get_data($urls->{'mlm'});

print Dumper($response);

# post new recipients to mlms 'mlm-test' and 'mlm-test1'
$data_hr = {
    mlm => 'mlm-test',
    address => ['neo@example.com', 'trinity@example.com']
};

$data_arr = [
    {
        mlm => 'mlm-test',
        address => ['neo@example.com', 'trinity@example.com', 'matrix@example.com']
    },
    {
        mlm => 'mlm-test1',
        address => ['agent_smith@example.com', 'white_rabbit@example.com']
    },
];

$data_err1 = [
    {
        mlm => 'nonexistent_mlm',
        address => ['neo@example.com']
    },
    {
        mlm => 'mlm-test',
        address => ['agent_smith@example.com']
    },
];

$data_err2 = [
    {
        mlm_err => 'mlm-test',
        address => ['neo@example.com']
    },
    {
        mlm => 'mlm-test1',
        address_err => ['agent_smith@example.com']
    },
];


$response_hr = django_post_data($urls->{'mlm'}, $data_hr);
print "The response code for hash ref is: " . $response_hr->responseCode() . "\n";
print "The response content for hash ref is: " . $response_hr->responseContent() . "\n";

$response_arr = django_post_data($urls->{'mlm'}, $data_arr);
print "The response code for array is: " . $response_arr->responseCode() . "\n";
print "The response content for array is: " . $response_arr->responseContent() . "\n";

$response_err1 = django_post_data($urls->{'mlm'}, $data_err1);
print "The response code for 1 nonexistent mlm: " . $response_err1->responseCode() . "\n";
print "The response content for 1 nonexistent mlm: " . $response_err1->responseContent() . "\n";

$response_err2 = django_post_data($urls->{'mlm'}, $data_err2);
print "The response code for error json: " . $response_err2->responseCode() . "\n";
print "The response content for error json: " . $response_err2->responseContent() . "\n";


sub django_get_data {
    my $url = shift;
    $client->GET($url, $headers);
    return decode_json($client->responseContent());
}

sub django_post_data {
    my $url = shift;
    my $data = shift;
    $client->POST($url, encode_json($data), $headers);    
}
