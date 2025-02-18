import csv
import pandas as pd
import boto3

ec2 = boto3.client('ec2', 
                aws_access_key_id='<AWS_ACCESS_KEYS>', 
                aws_secret_access_key='<AWS_SECRET_ACCESS_KEYS>', 
                region_name='<US_REGION>'
                )

def read_csv_file(file_path):
    try:
        # Method 1: Using csv module
        print("Reading with CSV module:")
        with open(file_path, 'r') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            
            # Print headers
            print("Headers:", csv_reader.fieldnames)
            print("-" * 50)
            
            # Print each row
            for row_number, row in enumerate(csv_reader, 1):
                print(f"Row {row_number}:")
                for key, value in row.items():
                    if (key == 'Identifier'):
                        result = get_snapshot_source_volume_instance(value)
                        print(result)
                    if (key == 'Service'):
                        print(f"{key}: {value}")
                    if (key == 'Identifier'):
                        print(f"{key}: {value}")
                    if (key == 'Tag: aws:backup:source-resource'):
                        print(f"{key}: {value}")


                

                print("-" * 50)


    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")


def get_snapshot_source_volume_instance(snapshot_arn):
    """
    Retrieves details about the source volume and attached EC2 instance
    from a given snapshot ARN.

    Args:
        snapshot_arn (str): The ARN of the EBS snapshot.

    Returns:
        dict: A dictionary containing details about the source volume and
              attached instance, or None if an error occurs or the resources
              are not found.  The dictionary structure is:
              {
                  'volume_id': str,
                  'volume_arn': str,
                  'instance_id': str,
                  'instance_arn': str,
                  'instance_state': str, # e.g. 'running', 'stopped'
                  'instance_name': str  # Best effort, might not be available
              }
        or None
    """

    try:
        

        # 1. Get Snapshot Details (to get Source Volume ID)
        snapshot_response = ec2.describe_snapshots(SnapshotIds=[snapshot_arn])

        if not snapshot_response['Snapshots']:
            print(f"Error: Snapshot {snapshot_arn} not found.")
            return None

        snapshot = snapshot_response['Snapshots'][0]
        volume_id = snapshot.get('VolumeId')

        if not volume_id:
            print(f"Error: Volume ID not found for snapshot {snapshot_arn}.")
            return None

        # 2. Get Volume Details (to get Volume ARN and attachment info)
        volume_response = ec2.describe_volumes(VolumeIds=[volume_id])

        if not volume_response['Volumes']:
            print(f"Error: Volume {volume_id} not found.")
            return None

        volume = volume_response['Volumes'][0]
        volume_arn = volume.get('VolumeArn')
        attachments = volume.get('Attachments', [])

        if not attachments:
            print(f"Error: Volume {volume_id} is not attached to any instance.")
            return None

        attachment = attachments[0]  # Assuming only one attachment
        instance_id = attachment.get('InstanceId')

        if not instance_id:
            print(f"Error: Instance ID not found for volume {volume_id}.")
            return None


        # 3. Get Instance Details (to get Instance ARN and Name)
        instance_response = ec2.describe_instances(InstanceIds=[instance_id])

        if not instance_response['Reservations'] or not instance_response['Reservations'][0]['Instances']:
            print(f"Error: Instance {instance_id} not found.")
            return None

        instance = instance_response['Reservations'][0]['Instances'][0]
        instance_arn = instance.get('InstanceArn')
        instance_state = instance.get('State', {}).get('Name') # Get the instance state
        
        # Try to get the instance name from tags:
        instance_name = None
        if 'Tags' in instance:
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                    break

        copy_tags_from_instance_to_snapshot(instance_id, snapshot_arn)

        return {
            'volume_id': volume_id,
            'volume_arn': volume_arn,
            'instance_id': instance_id,
            'instance_arn': instance_arn,
            'instance_state': instance_state,
            'instance_name': instance_name
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def copy_tags_from_instance_to_snapshot(instance_id, snapshot_id):
    """
    Copies all tags from an EC2 instance to an EBS snapshot.

    Args:
        instance_id (str): The ID of the EC2 instance.
        snapshot_id (str): The ID of the EBS snapshot.

    Returns:
        bool: True if tags were copied successfully, False otherwise.
        Prints informative messages to the console.
    """
    try:

        # 1. Get Instance Tags
        instance_response = ec2.describe_instances(InstanceIds=[instance_id])

        if not instance_response['Reservations'] or not instance_response['Reservations'][0]['Instances']:
            print(f"Error: Instance {instance_id} not found.")
            return False

        instance = instance_response['Reservations'][0]['Instances'][0]
        instance_tags = instance.get('Tags', [])

        if not instance_tags:
            print(f"Instance {instance_id} has no tags to copy.")
            return True  # Nothing to do, but consider it successful

        # 2. Create Tags for Snapshot (if any instance tags)
        if instance_tags:
            snapshot_tags = [{'Key': tag['Key'], 'Value': tag['Value']} for tag in instance_tags]  # format for CreateTags

            try:
                ec2.create_tags(Resources=[snapshot_id], Tags=snapshot_tags)
                print(f"Tags from instance {instance_id} copied to snapshot {snapshot_id}.")
                return True
            except Exception as e:
                print(f"Error creating tags on snapshot: {e}")
                return False

        return True  # If no instance tags, consider success.

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# Example usage
if __name__ == "__main__":
    csv_file_path = "resources.csv"  # Replace with your CSV file path
    read_csv_file(csv_file_path)
