# heatpumplogger
Repository to deploy the renewable forecast of ecowhen on an old LDC display using a rapberry pi


# setup services
```
<service_file> can be heatpump_logger or heatpump_dashboard

%create service file (use template.service in this repo)
cp template.service /etc/systemd/system/<service_file>.service 

%Reload the service files to include the new service.
sudo systemctl daemon-reload

% Apply correct rights to startup file
sudo chmod 744 <service_file>.sh 

%Start your service
sudo systemctl start <service_file>.service

%To enable your service on every reboot
sudo systemctl enable <service_file>.service

%To disable your service on every reboot
sudo systemctl disable <service_file>.service


```
# Operation

``` 
% restart deamon    
sudo systemctl restart <service_file>.service

% check status of deamon
sudo systemctl status  <service_file>.service
```
