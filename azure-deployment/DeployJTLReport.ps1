$ResourceGroup = "<ResourceGroup Name>"
$Storageaccountname = "<Storage account name>"
$storageKey = "<Storage key>"
$mongodbshareName = "<MongoDB Fileshare name >"
$postgresdbFileshare = "<postgresDB Fileshare name >"
$JWT_TOKEN = "27JU4qy73hchTMLoH8w9m"
$JWT_TOKEN_LOGIN = "GdK6TrCvX7rJRZJVg4ijt"



#create Postgres container
$postObj = @{ }
$postObj.Add("containerGroupName", "postgres")
$postObj.Add("Storageaccountname", $Storageaccountname)
$postObj.Add("storageKey", $storageKey)
$postObj.Add("postgresdbFileshare", $postgresdbFileshare)
$postgres = New-AzResourceGroupDeployment -name "postgres" -ResourceGroupName $ResourceGroup `
-TemplateParameterObject $postObj -TemplateFile "$($PSScriptRoot)\postgresARM.json"

$MyServer = $postgres.outputs.Values[0].value
$MyPort  = "5432"
$MyUid = "postgres"
$MyPass = "postgres"

$DBConnectionString = "Driver={PostgreSQL UNICODE(x64)};Server=$MyServer;Port=$MyPort;Uid=$MyUid;Pwd=$MyPass;"
$DBConn = New-Object System.Data.Odbc.OdbcConnection;
$DBConn.ConnectionString = $DBConnectionString;
$DBConn.Open();
$DBCmd = $DBConn.CreateCommand();
$DBCmd.CommandText = "CREATE DATABASE jtl_report;"
$DBCmd.ExecuteReader();
$DBConn.Close();

$DBConnectionString = "Driver={PostgreSQL UNICODE(x64)};Server=$MyServer;Port=$MyPort;Database=jtl_report;Uid=$MyUid;Pwd=$MyPass;"
$DBConn = New-Object System.Data.Odbc.OdbcConnection;
$DBConn.ConnectionString = $DBConnectionString;
$DBConn.Open();
$DBCmd = $DBConn.CreateCommand();
$DBCmd.CommandText = 'CREATE EXTENSION "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS jtl;

CREATE TABLE jtl.projects(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_name character varying(50) NOT NULL UNIQUE
);

CREATE TABLE jtl.items (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_name character varying(40) NOT NULL,
    project_id uuid NOT NULL REFERENCES jtl.projects(id),
    jtl_data jsonb NOT NULL,
    note character varying(150),
    environment character varying(20),
    upload_time timestamp without time zone DEFAULT now(),
    start_time timestamp without time zone,
    duration integer
);

CREATE TABLE jtl.item_stat (
    id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
    item_id uuid NOT NULL REFERENCES jtl.items(id),
    stats jsonb NOT NULL
);
';
$DBCmd.ExecuteReader();
$DBConn.Close();

#Run migrate container 
$DATABASE_URL = "postgres://postgres:postgres@$($MyServer):5432/jtl_report"
$postObj = @{ }
$postObj.Add("containerGroupName", "migration")
$postObj.Add("DATABASE_URL", $DATABASE_URL)
$postObj.Add("JWT_TOKEN_LOGIN", $JWT_TOKEN_LOGIN)
$postObj.Add("JWT_TOKEN", $JWT_TOKEN)

$postgres = New-AzResourceGroupDeployment -name "Migration" -ResourceGroupName $ResourceGroup `
-TemplateParameterObject $postObj -TemplateFile "$($PSScriptRoot)\Migration.json"


#Run other containers
$postObj = @{ }
$postObj.Add("containerGroupName", "jtlreportr")
$postObj.Add("Storageaccountname", $Storageaccountname)
$postObj.Add("storageKey", $storageKey)
$postObj.Add("JWT_TOKEN", $JWT_TOKEN)
$postObj.Add("JWT_TOKEN_LOGIN", $JWT_TOKEN_LOGIN)
$postObj.Add("PostgresIP", $MyServer)
$postObj.Add("mongodbshareName", $mongodbshareName)

$postgres = New-AzResourceGroupDeployment -name "JtlReporter" -ResourceGroupName $ResourceGroup `
-TemplateParameterObject $postObj -TemplateFile "$($PSScriptRoot)\JtlReporterArm.json"

