### 1.计算crc 16

```C
static uint16_t Cal_CRC16(const uint8_t* data, uint32_t size){
        uint32_t crc = 0;
        const uint8_t* dataEnd = data+size;
        while(data < dataEnd){
                crc = UpdateCRC16(crc, *data++);
        }
        crc = UpdateCRC16(crc, 0);
        crc = UpdateCRC16(crc, 0);
        return crc&0xffffu;
}
```

### 2.ymodem文件传输

```c
/*
/////////////////////////////// ymodem 发送升级文件（供上位机参考）/////////////////////////////////////////
//准备第一个要发送的包
static void Ymodem_PrepareIntialPacket(uint8_t *data, const uint8_t* fileName, uint32_t *length){
	uint16_t i, j;
	uint8_t file_ptr[10];
	// 第一包数据的前三个字符
	data[0] = SOH; // soh表示数据包是128字节
	data[1] = 0x00;
	data[2] = 0xff;
	// 文件名
	for(i=0; (fileName[i]!='\0')&&(i<FILE_NAME_LENGTH); i++){
		data[i+PACKET_HEADER] = fileName[i];
	}
	data[i+PACKET_HEADER] = 0x00;
	// 文件大小转换成字符
	Int2Str (file_ptr, *length);
	for (j=0, i=i+PACKET_HEADER+1; file_ptr[j]!='\0'; ){
		data[i++] = file_ptr[j++];
	}
	// 其余补0
	for (j=i; j<PACKET_SIZE+PACKET_HEADER; j++){
		data[j] = 0;
	}
}

//发送bin，打包
//SourceBuf 要发送的原数据
//data      最终要发送的数据包，已经包含的头文件和原数据
//pktNo     数据包序号
//sizeBlk   要发送数据数
static void Ymodem_PreparePacket(uint8_t *SourceBuf, uint8_t *data, uint8_t pktNo, uint32_t sizeBlk){
	uint16_t i, size, packetSize;
	uint8_t* file_ptr;
	// 设置好要发送数据包的前三个字符data[0]，data[1]，data[2]
	// 根据sizeBlk的大小设置数据区数据个数是取1024字节还是取128字节
	packetSize = sizeBlk >= PACKET_1K_SIZE ? PACKET_1K_SIZE : PACKET_SIZE;
	// 数据大小进一步确定
	size = sizeBlk < packetSize ? sizeBlk :packetSize;
	// 首字节：确定是1024字节还是用128字节
	if (packetSize == PACKET_1K_SIZE){
		data[0] = STX;
	}else{
		data[0] = SOH;
	}
	data[1] = pktNo;	// 第2个字节：数据序号
	data[2] = (~pktNo);	// 第3个字节：数据序号取反
	file_ptr = SourceBuf;
	// 填充要发送的原始数据
	for (i = PACKET_HEADER; i < size + PACKET_HEADER;i++){
		data[i] = *file_ptr++;
	}
	// 不足的补 EOF (0x1A) 或 0x00
	if ( size  <= packetSize){
		for (i = size + PACKET_HEADER; i < packetSize + PACKET_HEADER; i++){
			data[i] = 0x1A; // EOF (0x1A) or 0x00
		}
	}
}

//ymodem发送数据包
static void Ymodem_SendPacket(uint8_t *data, uint16_t length){
	uint16_t i;
	i = 0;

	while (i < length){
		Send_Byte(data[i]);
		i++;
	}
}

//ymodem和校验
static uint8_t CalChecksum(const uint8_t* data, uint32_t size){
  uint32_t sum = 0;
  const uint8_t* dataEnd = data+size;

  while(data < dataEnd ){
    sum += *data++;
  }
  return (sum & 0xffu);
}

//Ymodem 数据发送
//buf:           文件数据
//sendFileName:  文件名
//sizeFile:      文件大小
//返回0：		 文件发送成功
uint8_t Ymodem_Transmit (uint8_t *buf, const uint8_t* sendFileName, uint32_t sizeFile){
	uint8_t packet_data[PACKET_1K_SIZE + PACKET_OVERHEAD];
	uint8_t filename[FILE_NAME_LENGTH];
	uint8_t *buf_ptr, tempCheckSum;
	uint16_t tempCRC;
	uint16_t blkNumber;
	uint8_t receivedC[2], CRC16_F = 0, i;
	uint32_t errors, ackReceived, size = 0, pktSize;

	errors = 0;
	ackReceived = 0;
	for (i = 0; i < (FILE_NAME_LENGTH - 1); i++){
		filename[i] = sendFileName[i];
	}
	CRC16_F = 1;
	// 初始化要发送的第一个数据包
	Ymodem_PrepareIntialPacket(&packet_data[0], filename, &sizeFile);
	do{
		// 发送数据包
		Ymodem_SendPacket(packet_data, PACKET_SIZE + PACKET_HEADER);
		// 根据CRC16_F发送CRC或者求和进行校验
		if (CRC16_F){
			tempCRC = Cal_CRC16(&packet_data[3], PACKET_SIZE);
			Send_Byte(tempCRC >> 8);
			Send_Byte(tempCRC & 0xFF);
		}else{
			tempCheckSum = CalChecksum (&packet_data[3], PACKET_SIZE);
			Send_Byte(tempCheckSum);
		}
		// 等待 Ack 和字符 'C'
		if (Receive_Byte(&receivedC[0], 10000) == 0){
			if (receivedC[0] == ACK){
				// 接收到应答
				ackReceived = 1;
			}
		}else{		// 没有等到
			errors++;
		}
	// 发送数据包后接收到应答或者没有等到就推出
	}while(!ackReceived && (errors < 0x0A));
	// 超过最大错误次数就退出
	if (errors >=  0x0A){
		return errors;
	}
	buf_ptr = buf;
	size = sizeFile;
	blkNumber = 0x01;
	// 下面使用的是发送1024字节数据包
	// Resend packet if NAK  for a count of 10 else end of communication
	while (size){
		// 准备下一包数据
		Ymodem_PreparePacket(buf_ptr, &packet_data[0], blkNumber, size);
		ackReceived = 0;
		receivedC[0]= 0;
		errors = 0;
		do{
			// 发送下一包数据
			if (size >= PACKET_1K_SIZE){
				pktSize = PACKET_1K_SIZE;
			}else{
				pktSize = PACKET_SIZE;
			}
			Ymodem_SendPacket(packet_data, pktSize + PACKET_HEADER);
			// 根据CRC16_F发送CRC校验或者求和的结果
			if (CRC16_F){
				tempCRC = Cal_CRC16(&packet_data[3], pktSize);
				Send_Byte(tempCRC >> 8);
				Send_Byte(tempCRC & 0xFF);
			}else{
				tempCheckSum = CalChecksum (&packet_data[3], pktSize);
				Send_Byte(tempCheckSum);
			}
			// 等到Ack信号
			if ((Receive_Byte(&receivedC[0], 100000) == 0)  && (receivedC[0] == ACK)){
				ackReceived = 1;
				// 修改buf_ptr位置以及size大小，准备发送下一包数据
				if (size > pktSize){
					buf_ptr += pktSize;
					size -= pktSize;
					if (blkNumber == (2*1024*1024/128)){
						return 0xFF; // 错误
					}else{
						blkNumber++;
					}
				}else{
					buf_ptr += pktSize;
					size = 0;
				}
			}else{
				errors++;
			}

		}while(!ackReceived && (errors < 0x0A));
		// 超过10次没有收到应答就退出
		if (errors >=  0x0A){
			return errors;
		}
	}

	ackReceived = 0;
	receivedC[0] = 0x00;
	errors = 0;
	do{
		Send_Byte(EOT);
		// 发送EOT信号
		// 等待Ack应答
		if((Receive_Byte(&receivedC[0], 10000) == 0) && receivedC[0] == ACK){
			ackReceived = 1;
		}else{
			errors++;
		}
	}while(!ackReceived && (errors < 0x0A));
	// 超过10次没有收到应答就退出
	if (errors >=  0x0A){
		return errors;
	}
	// 初始化最后一包要发送的数据
	ackReceived = 0;
	receivedC[0] = 0x00;
	errors = 0;

	packet_data[0] = SOH;
	packet_data[1] = 0;
	packet_data [2] = 0xFF;
	// 数据包的数据部分全部初始化为0
	for(i=PACKET_HEADER; i < (PACKET_SIZE+PACKET_HEADER); i++){
		packet_data [i] = 0x00;
	}
	do{
		// 发送数据包
		Ymodem_SendPacket(packet_data, PACKET_SIZE + PACKET_HEADER);
		// 根据CRC16_F发送CRC校验或者求和的结果
		tempCRC = Cal_CRC16(&packet_data[3], PACKET_SIZE);
		Send_Byte(tempCRC >> 8);
		Send_Byte(tempCRC & 0xFF);
		// 等待 Ack 和字符 'C'
		if (Receive_Byte(&receivedC[0], 10000) == 0){
			if (receivedC[0] == ACK){
				// 数据包发送成功
				ackReceived = 1;
			}
		}else{
			errors++;
		}
	}while (!ackReceived && (errors < 0x0A));
	// 超过10次没有收到应答就退出
	if (errors >=  0x0A){
		return errors;
	}
	do{
		Send_Byte(EOT);
		// 发送EOT信号
		// 等待Ack应答
		if ((Receive_Byte(&receivedC[0], 10000) == 0)  && receivedC[0] == ACK){
			ackReceived = 1;
		}else{
			errors++;
		}
	}while (!ackReceived && (errors < 0x0A));

	if (errors >=  0x0A){
		return errors;
	}
	return 0; //文件发送成功
}
*/

```
