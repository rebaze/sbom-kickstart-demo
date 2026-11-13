package demo.portal;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Accepts a partner's order as JSON and logs it. Enough code to give the build real dependencies. */
public final class OrderIntake {
    private static final Logger LOG = LogManager.getLogger(OrderIntake.class);
    private static final ObjectMapper JSON = new ObjectMapper();

    private OrderIntake() {
    }

    public static void main(String[] args) throws Exception {
        String payload = args.length > 0 ? args[0] : "{\"partner\":\"demo\",\"items\":1}";
        Map<?, ?> order = JSON.readValue(payload, Map.class);
        LOG.info("order from {}", StringUtils.abbreviate(String.valueOf(order.get("partner")), 40));
    }
}
