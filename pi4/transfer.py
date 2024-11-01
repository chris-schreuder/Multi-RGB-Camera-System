import paramiko
from scp import SCPClient
from tqdm import tqdm
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


# def download_cam(hostname, username):
#     port = 22
#     password = 'pass'  # replace with the actual password

#     # The path to the folder on the Raspberry Pi that you want to transfer
#     remote_folder_path = f'/home/{username}/data'
#     # The path to the destination on the laptop
#     local_destination_path = f'data'

#     def create_ssh_client(hostname, port, username, password):
#         """Creates an SSH client to connect to the Raspberry Pi."""
#         client = paramiko.SSHClient()
#         client.load_system_host_keys()
#         client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#         client.connect(hostname, port, username, password)
#         return client

#     def get_file_list(ssh_client, remote_folder):
#         """Gets a list of all files in the remote folder."""
#         stdin, stdout, stderr = ssh_client.exec_command(f'find {remote_folder} -type f')
#         files = stdout.read().decode().split()
#         return files

#     def transfer_folder(ssh_client, remote_folder, local_path):
#         """Transfers a folder from the Raspberry Pi to the laptop with progress tracking."""
#         files = get_file_list(ssh_client, remote_folder)
#         file_count = len(files)
#         print(f'Files: {file_count}')
        
#         with SCPClient(ssh_client.get_transport()) as scp:
#             with tqdm(total=file_count, desc="Transferring files", unit="file") as pbar:
#                 for file in files:
#                     remote_file = file
#                     local_file = os.path.join(local_path, os.path.relpath(file, remote_folder))
#                     os.makedirs(os.path.dirname(local_file), exist_ok=True)
#                     scp.get(remote_file, local_file)
#                     pbar.update(1)

#     # Create an SSH client
#     ssh_client = create_ssh_client(hostname, port, username, password)

#     # Transfer the folder
#     transfer_folder(ssh_client, remote_folder_path, local_destination_path)

#     # Close the SSH connection
#     ssh_client.close()

#     print("Folder transfer complete.")

hostnames = ['PI1_IP', 'PI2_IP', 'PI3_IP', 'PI4_IP', 'PI5_IP', 'PI6_IP']
usernames = ['pi1', 'pi2', 'pi3', 'pi4', 'pi5', 'pi6']
for hostname, username in zip(hostnames, usernames):
    # Raspberry Pi connection details
    port = 22
    password = 'pass'  # replace with the actual password

    # The path to the folder on the Raspberry Pi that you want to transfer
    remote_folder_path = f'/home/{username}/data'
    # The path to the destination on the laptop
    local_destination_path = f'data'

    def create_ssh_client(hostname, port, username, password):
        """Creates an SSH client to connect to the Raspberry Pi."""
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port, username, password)
        return client

    def get_file_list(ssh_client, remote_folder):
        """Gets a list of all files in the remote folder."""
        stdin, stdout, stderr = ssh_client.exec_command(f'find {remote_folder} -type f')
        files = stdout.read().decode().split()
        return files

    def transfer_folder(ssh_client, remote_folder, local_path):
        """Transfers a folder from the Raspberry Pi to the laptop with progress tracking."""
        files = get_file_list(ssh_client, remote_folder)
        file_count = len(files)
        print(f'Files: {file_count}')
        
        with SCPClient(ssh_client.get_transport()) as scp:
            with tqdm(total=file_count, desc="Transferring files", unit="file") as pbar:
                for file in files:
                    remote_file = file
                    local_file = os.path.join(local_path, os.path.relpath(file, remote_folder))
                    os.makedirs(os.path.dirname(local_file), exist_ok=True)
                    scp.get(remote_file, local_file)
                    pbar.update(1)

        # def download_file(scp, remote_file, local_file):
        #     os.makedirs(os.path.dirname(local_file), exist_ok=True)
        #     scp.get(remote_file, local_file)

        # with SCPClient(ssh_client.get_transport()) as scp:
        #     with tqdm(total=len(files), desc="Transferring files", unit="file") as pbar:
        #         with ThreadPoolExecutor() as executor:
        #             future_to_file = {
        #                 executor.submit(download_file, scp, file, os.path.join(local_path, os.path.relpath(file, remote_folder))): file
        #                 for file in files
        #             }
        #             for future in as_completed(future_to_file):
        #                 future.result()  # This will raise an exception if the download failed
        #                 pbar.update(1)

    # Create an SSH client
    ssh_client = create_ssh_client(hostname, port, username, password)

    # Transfer the folder
    transfer_folder(ssh_client, remote_folder_path, local_destination_path)

    # Close the SSH connection
    ssh_client.close()

    print("Folder transfer complete.")
