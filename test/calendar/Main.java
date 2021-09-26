import java.nio.*;
import java.util.*;
import java.nio.charset.StandardCharsets;

class Main {
  public static void main(String[] args) {
    
    System.out.println("Hello world!");

    byte SOH = 1;
    byte DLE = 16;
    byte ETX = 3;

    byte[] msgArr = new byte[19];
    msgArr[0] = DLE;
    msgArr[1] = SOH;
    msgArr[2] = 16;
    // byte array is initially filled with 0x00, so strings will
    // automatically be padded as in request string
    ByteBuffer buf = ByteBuffer.wrap(msgArr);
    buf.order(ByteOrder.LITTLE_ENDIAN);
    buf.position(3);
    Calendar cal = Calendar.getInstance();
    // cal.setTime(date);
    buf.putShort((short) cal.get(Calendar.SECOND));
    buf.putShort((short) cal.get(Calendar.MINUTE));
    buf.putShort((short) cal.get(Calendar.HOUR_OF_DAY));
    buf.putShort((short) cal.get(Calendar.DAY_OF_MONTH));
    buf.putShort((short) (cal.get(Calendar.DAY_OF_WEEK) - 1));
    buf.putShort((short) cal.get(Calendar.MONTH));
    // Assumption: year is in yyyy format.
    buf.putShort((short) cal.get(Calendar.YEAR));
    msgArr[17] = DLE;
    msgArr[18] = ETX;

    // Test printout of Message
    // System.out.println(msgArr);
    System.out.println("MESSAGE: ");
    System.out.println("SECOND: "          + cal.get(Calendar.SECOND));
    System.out.println("MINUTE: "          + cal.get(Calendar.MINUTE));
    System.out.println("HOUR: "            + cal.get(Calendar.HOUR_OF_DAY));
    System.out.println("DAY OF MONTH: "    + cal.get(Calendar.DAY_OF_MONTH));
    System.out.println("DAY OF WEEK: "     + (cal.get(Calendar.DAY_OF_WEEK) - 1));
    System.out.println("MONTH: "           + cal.get(Calendar.MONTH));
    System.out.println("YEAR: "            + cal.get(Calendar.YEAR));
    System.out.println(Arrays.toString(msgArr));
    for (int j=0; j < msgArr.length; j++) {
        System.out.format("%02X ", msgArr[j]);
    }
    System.out.println();
    
    }
}