import re 

def parse_message2(message):
    """
    The Delphi Track system send 3 messages during the syncing process.
    Message 2 contains the time and date information set on the track system.
    """
    message_pair = re.findall('..?', message)
    message_bytes = []
    message_int = []
    message_parsed = {}
    
    for pair in message_pair:
        byte_val = bytes.fromhex(pair)
        int_val = int.from_bytes(byte_val, "little", signed="True")
    
        message_bytes.append(byte_val)
        message_int.append(int_val)
    
    year_int = int.from_bytes(message_bytes[15] + message_bytes[16], "little", signed="True")
    
    message_parsed["second"]        = message_int[3]
    message_parsed["minute"]        = message_int[5]
    message_parsed["hour"]          = message_int[7]
    message_parsed["dayofmonth"]    = message_int[9] # maybe add 1 here bc track subtracts 1
    message_parsed["dayofweek"]     = message_int[11]
    message_parsed["month"]         = message_int[13]
    message_parsed["year"]          = year_int
    
    print("MESSAGE PARSED: ", message_parsed)
    
    return message_parsed
    
if __name__ == "__main__":
    message = "100110340014001500140002000600E507100378" # from dtrack
    # message = "10011023000A000A001B0002000600E5071003" # from java test
    parse_message2(message)
    
    
    
    
    
    

